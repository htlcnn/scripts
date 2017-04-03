def rotate_pdf(how={'all':0}, folder='.'):
    '''Rotate pdf files in a folder
    how: dict of degree to rotate for each type
    - all: all pages
    - even: even pages
    - odd: odd pages
    pagenum starts from 0, a little bit tricky
    '''
    for file in os.listdir(folder):
        filename = file[:file.rfind('.')]
        ext = file[file.rfind('.')+1:]
        if ext == 'pdf':
            file_path = os.path.join(folder, file)
            pdf_in = open(file_path, 'rb')
            pdf_reader = PyPDF2.PdfFileReader(pdf_in)
            pdf_writer = PyPDF2.PdfFileWriter()
            
            for pagenum in range(pdf_reader.numPages):
                page = pdf_reader.getPage(pagenum)
                if how.get('all'):
                    page.rotateClockwise(how.get('all'))
                elif pagenum % 2 == 0 and how.get('odd'):
                    page.rotateClockwise(how.get('odd'))
                elif pagenum % 2 == 1 and how.get('even'):
                    page.rotateClockwise(how.get('even'))
                pdf_writer.addPage(page)
                
            rotated_file_path = os.path.join(folder, '%s_rotated.%s' % (filename, ext))
            pdf_out = open(rotated_file_path, 'wb')
            pdf_writer.write(pdf_out)
            pdf_out.close()
            pdf_in.close()
