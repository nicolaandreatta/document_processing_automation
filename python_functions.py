## Import libraries
import cv2
import os
import pytesseract
from skimage import *
from deskew import determine_skew
import re
import numpy as np
import logging
import time
from PIL import Image

## Set Tesseract directory
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

## Define functions
def noise_removal_and_smoothening(img):
    img_u=img.astype(np.uint8)
    filtered = cv2.adaptiveThreshold(img_u, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 41,3)
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(filtered, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    #image smoothening
    ret1, th1 = cv2.threshold(img_u, 180, 255, cv2.THRESH_BINARY)
    ret2, th2 = cv2.threshold(th1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur = cv2.GaussianBlur(th2, (1, 1), 0)
    ret3, th3 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    or_image = cv2.bitwise_or(th3, closing)
    return or_image

def adjust_contrast(img, clipLimit, tileGridSize, brightness, contrast):
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize)
        cl = clahe.apply(l_channel)
        limg = cv2.merge((cl,a,b))
        enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    except:
        img = np.int16(img)
        img = img * (contrast/127+1) - contrast + brightness
        img = np.clip(img, 0, 255)
        img = np.uint8(img)
        enhanced_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return enhanced_img

def deskew(image, dimension_limit):
    '''
    Rotate the image automatically to increase the OCR precision. If the image is too big,
    the function will interrupt the process and the original image is returned
    '''
    if image.shape[0] > dimension_limit:
        print('The image has not been processed because over the dimension_limit')
        return image.astype(np.uint8)
    else:
        angle = determine_skew(image)
        if angle == None:
            rotated = rotate(image, 0, resize=True, preserve_range=False) * 255
            print('angle was not calculated by the function. Rotation is se to angle = 0')
        else:
            _t_start = time.time()
            rotated = rotate(image, angle, resize=True, preserve_range=False) * 255
            _t_end = time.time()
            print('Image rotated, angle = {a}'.format(a=angle))
            print('Deskew execution time {b}'.format(b=round(_t_end-_t_start, 2)))
        return rotated.astype(np.uint8)

def process_image_for_ocr(im, _noise_removal=True, _contrast=True, _deskew=True):
    im_arr = np.asarray(im)
    im_arr_g = cv2.cvtColor(im_arr, cv2.COLOR_RGB2GRAY)
    if _noise_removal:
        im_arr_g = noise_removal_and_smoothening(im_arr_g)
        print('Noise and Smoothness adjustments completed')
    if _contrast:
        im_arr_g = adjust_contrast(im_arr_g, 1.5, (4,4), 50, 30, False, (1400, 900), False)
        print('Contrast and Brightness adjustment completed')
    if _deskew:
        im_arr_g = deskew(im_arr_g, 4000)
        print('Image rotation adjustment completed')
    return im_arr_g

def ocr_text_extracion(img, prefix, suffix, lang):
    '''
    The function perform OCR image_to_string().
    The user could add a prefix and a suffix to the generated string.
    '''
    _t_start = time.time()
    __temp_string = pytesseract.image_to_string(img, lang=lang)
    _t_end = time.time()
    print('OCR process completed in {a} seconds'.format(a=round(_t_end-_t_start, 2)))
    return prefix + ' ' + __temp_string + ' ' + suffix
    
## scan document page for image generation and OCR
def text_image_page_scanner(page, doc, doc_name, num_chars, width_size, height_size, path_to_img, image_preprocessing=True):
    '''
    - The function returns the text content of a PDF page imported using PyMuPDF.
    - The num_chars parameter controls the min lenght of characters to skip the OCR
    and extract the text directly. if there are less characters than this parameter
    the function returns the image(s) in the page. Also, if the text contains strange
    characters (bytes like), the entire page will be scanned and the OCR will be run.
    - The images are filtered according to their dimentions: (width_size, height_size)
    if the page contains 1 image, then the runs over the only image in the page.
    if the page contains >1 images larger than the 'width and height' filter,
    the function scans the entire page and returns a png of the page. 
    '''
    _num_page = page.number
    _page_text = page.get_text()
    _doc_page_tag_string = ' - (document: {a}, page {b})'.format(a=doc_name, b=_num_page)
    prefix='OCR extraction start:'
    suffix='OCR extraction end'
    if len(_page_text) > num_chars:
        print('Text extraction returns more than {a} characters'.format(a=num_chars))
        print('for page {b}. OCR procedure is not necessary'.format(b=_num_page))
        
        if _page_text.find('\x01') + _page_text.find('\x02') + _page_text.find('\x03') > 0:
            print('The string contains unknown characters. The entire page will be scanned')
            _page_scan = page.get_pixmap(alpha=False, dpi=300, colorspace='rgb')
            img = Image.frombytes('RGB', [_page_scan.width, _page_scan.height], _page_scan.samples)
            
            if image_preprocessing:
                img_postprocess = process_image_for_ocr(img)
            else:
                img_postprocess = img
            
            _text_from_img = ocr_text_extracion(img_postprocess, prefix, suffix, 'ita')
            _tag_string ='Page OCR scan' + _doc_page_tag_string
            return _tag_string + ' - ' + _text_from_img + ' - ' + _tag_string
        else:
            _tag_string = 'Direct text extraction' + _doc_page_tag_string
            return _tag_string + ' START - ' + _page_text + ' - END ' + _tag_string
    else:
        print('The page {a} does not contain text. OCR procedure is initialized'.format(a=_num_page))
        imgpage = page.get_image_info(xrefs=True)
        print('{a} image(s) found in page {b}.'.format(a=len(imgpage), b=_num_page))
        _cleaned_images = [k for k in imgpage if (k['width'] > width_size) and (k['height'] > height_size)]

        if len(_cleaned_images) == 0:
            print('No images found in page {a}. page scan using pixmap will start'.format(a=_num_page))
            _page_scan = page.get_pixmap(alpha=False, dpi=300, colorspace='rgb')
            img = Image.frombytes('RGB', [_page_scan.width, _page_scan.height], _page_scan.samples)

        elif len(_cleaned_images) == 1:
            print('One image found in page {a}. Image extraction using PyMuPDF'.format(a=_num_page))
            __img = _cleaned_images[0]
            _img_xref, _img_wdh, _img_hgt = __img['xref'], __img['width'], __img['height']
            print('Analyzing image with xref = {b}'.format(b=_img_xref))
            print('Image xref {c} resolution = {a}'.format(a=(_img_wdh, _img_hgt), c=_img_xref))
            _image_dict = doc.extract_image(_img_xref)
            _img_ext = _image_dict.get('ext')
            _path_to_image = path_to_img + '/' + doc_name + '_img_xref{z}_{p}.{a}'.format(a=_img_ext, p=page.number, z=_img_xref)
            img = open(_path_to_image, "wb")
            img.write(_image_dict.get('image'))
            img.close()
            print('Image created. Path to the image is {a}'.format(a=_path_to_image))
            img = cv2.imread(_path_to_image)
            print('Image reimported')
            os.remove(_path_to_image)
            print('Image deleted')

        elif len(_cleaned_images) > 1:
            print('{c} image(s) found at the'.format(c=len(_cleaned_images)))
            print('page {a}. page scan using pixmap will start'.format(a=_num_page))
            _page_scan = page.get_pixmap(alpha=False, dpi=300, colorspace='rgb')
            img = Image.frombytes('RGB', [_page_scan.width, _page_scan.height], _page_scan.samples)

        if image_preprocessing:
            img_postprocess = process_image_for_ocr(img)
        else:
            img_postprocess = img
        
        if img_postprocess.shape[0] < 4000:
            _text_from_img = ocr_text_extracion(img_postprocess, prefix, suffix, 'ita')
        else:
            return 'Memory limit reached ' + _doc_page_tag_string + ' START - END'

        '''
        This further step is for some rare cases in which the text extraction from images is
        empty and the image is almost completely white (images with rgb>254). This is the case
        of some pdfs with no written text, one white image as a background and several images
        with some actual text but smaller than the size filter of (500px X 500px).
        The solution is an entire page scan
        '''
        if len(_text_from_img)-(len(prefix)+len(suffix))<=0 and img_postprocess.mean()>254:
            print('image {c} text extraction is empty.'.format(c=len(_cleaned_images)))
            print('The entire page {a} will be scanned using the pixmap'.format(a=_num_page))
            _page_scan = page.get_pixmap(alpha=False, dpi=300, colorspace='rgb')
            img = Image.frombytes('RGB', [_page_scan.width, _page_scan.height], _page_scan.samples)
            if image_preprocessing:
                img_postprocess = process_image_for_ocr(img)
            else:
                img_postprocess = img
            if img_postprocess.shape[0] <4000:
                _text_from_img = ocr_text_extracion(img_postprocess, prefix, suffix, 'ita')
            else:
                return 'Memory limit reached ' + _doc_page_tag_string + ' START - END'

        _tag_string = 'OCR extraction ' + _doc_page_tag_string
        return _tag_string + ' - ' + _text_from_img + ' - ' + _tag_string

def txt_cleaner(txt, basic_operation=True):
    regex = r'\\r|\\n|\r|\r\n'
    regex2 = r' +'
    regex3 = r'\n \n'
    if basic_operation:
        txt = re.sub(regex, '\n', txt)
        txt = re.sub(regex2, ' ', txt)
        txt = re.sub(regex3, '\n\n', txt)
        print('Text cleaned according to specified operation(s)')
    else:
        txt = txt
        print('Function returned the original text')
    return txt
