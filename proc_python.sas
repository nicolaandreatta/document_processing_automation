/* -- PROC PYTHON: PDF file OCR and elaborations -- */
filename pyfunc "/mnt/nfs/viya/python_functions/ocr_image_txt_processing_functions.py";
proc python infile=pyfunc restart;
submit;

## import libraries
import time
import os
import logging
import pandas as pd
import fitz
import shutil

## bring paths into python
path_to_sin_folders = SAS.symget('path_to_sin_folders')
path_to_temp_data = SAS.symget('path_to_temp_data')
path_to_metadata_out = SAS.symget('path_to_metadata_out')
path_to_sin_folders_out = SAS.symget('path_to_sin_folders_out')
path_to_log = SAS.symget('path_to_log')
path_to_sin_move = SAS.symget('path_to_sin_move')
timestamp_macro = SAS.symget('timestamp')

## log configuration
log_file = os.path.join(path_to_log, 'ocr_{a}.log'.format(a=timestamp_macro))
logging.basicConfig(filename=log_file,
                    filemode='w', 
                    level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] - %(message)s')

## PDF reading
list_folder_file = os.listdir(path_to_sin_folders)
list_folder = [k for k in list_folder_file if os.path.isdir(path_to_sin_folders+'/'+k)]

start_time_all = time.time()
for _dir in list_folder:
    start_time_dir = time.time()
    logging.debug('Working on Folder {a}'.format(a=_dir))
    _new_folder_output = os.path.join(path_to_sin_folders_out, _dir)
    if os.path.isdir(_new_folder_output):
        logging.debug('The output folder {a} already exists. Files will be overwrited'.format(a=_dir))
        pass
    else:
        os.mkdir(_new_folder_output)
        logging.debug('Output folder {a} created'.format(a=_dir))
    _get_files = os.listdir(path_to_sin_folders+'/'+_dir)
    _get_files = [k for k in _get_files if k.lower().endswith('.pdf')]
    _text_file = []
    _medatada_file = []
    for _file in _get_files:
        start_time_file = time.time()
        _path_to_file = path_to_sin_folders+'/'+_dir+'/'+_file
        logging.debug('Working on file {a}'.format(a=_file))
        doc = fitz.open(_path_to_file)
        metadata = pd.DataFrame(doc.metadata, index=[_file])
        metadata['page_num'] = len(doc)
        metadata['fileName'] = _file.split('.')[0]
        metadata['FolderName'] = _dir
        _medatada_file.append(metadata)
        __text_page = []
        for page in doc:
            logging.debug('Working on page {a} of the file {b}'.format(a=page.number, b=_file))
            doc_name_list =_file.split('.')[:-1]
            doc_name= ("".join(doc_name_list))
            try:
                text = text_image_page_scanner(page, doc, doc_name, 50, 500, 500, path_to_temp_data, image_preprocessing=True)
                text = '#### Complete extraction: -> ' + text + ' ####'
                logging.debug('Text extraction completed in file {a}, page {b}'.format(a=_file, b=page.number))
            except:
                logging.debug('Text extraction FAILED in file {a}, page {b}'.format(a=_file, b=page.number))
                text = ''
                text = '#### Empty extraction: -> ' + text + ' ####'
                continue
            __text_page.append(text)
        _text_file = '\n\n'.join([k for k in __text_page])
        logging.debug('Concatenation of all pages of file {a} completed'.format(a=_file))
        logging.debug('Execution on file {a} completed in {b} seconds'.format(a=_file, b=round((time.time() - start_time_file), 2)))
        with open(_new_folder_output+'/{a}.txt'.format(a=doc_name),'w',encoding='utf-8') as f:
            txt = txt_cleaner(_text_file, basic_operation=True)
            f.write(txt)
            f.close()
            logging.debug('{a}.txt file created'.format(a=_file))
    logging.debug('Execution on folder {a} completed in {b} seconds'.format(a=_dir, b=round((time.time() - start_time_dir), 2)))
    shutil.move(os.path.join(path_to_sin_folders, _dir), os.path.join(path_to_sin_move, _dir))
    logging.debug('Folder {a} moved to path {b}\n\n'.format(a=_dir, b=path_to_sin_move))
    df_metadata_all = pd.concat(_medatada_file, axis=0)
    df_metadata_all.to_csv(path_to_metadata_out+'/metadata_{a}.csv'.format(a=_dir))
logging.debug("Execution time all SIN: {a} seconds\n".format(a=round((time.time() - start_time_all), 2)))

endsubmit;
quit;
