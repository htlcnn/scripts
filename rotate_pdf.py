'''
A script to rotate my pdf files created from the scanner.
I use Fuji Xerox Docucentre-IV 4070 to scan my documents with duplex mode.
In order to speed up the scanning job, I rotate the original documents so that
the scanner rolls along the short side of the paper. The output pdf will be
rotated -90 and -270 degree one page after each other. So I wrote this script
to mass rotate pdf files in a folder. You might customize it to your own use.
Usage:
    python rotate_pdf.py [-f folder_path] [--all 0]  [--odd 0] [--even 0]
    f: Path of folder that your pdf files reside, default current folder
    all: degree to rotate all pages, defaults to 0
    odd: degree to rotate odd pages, defaults to 90
    even: degree to rotate even pages, defaults to 270
'''
import argparse
import os
import PyPDF2


def rotate_pdf(folder='.', how={'all': 0}):
    '''Rotate pdf files in a folder
    how: dict of degree to rotate for each type
    - all: all pages
    - even: even pages
    - odd: odd pages
    pagenum starts from 0, a little bit tricky
    '''
    for file in os.listdir(folder):
        filename = file[:file.rfind('.')]
        ext = file[file.rfind('.') + 1:]
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

            rotated_file_path = os.path.join(folder,
                                             '%s_rotated.%s' % (filename, ext))
            pdf_out = open(rotated_file_path, 'wb')
            pdf_writer.write(pdf_out)
            pdf_out.close()
            pdf_in.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder',
                        help='Folder where pdf files are rotated',
                        default='.')
    parser.add_argument('--all', help='Rotate all pages by x degree',
                        type=int, default=0)
    parser.add_argument('--odd', help='Rotate odd pages by x degree',
                        type=int, default=90)
    parser.add_argument('--even', help='Rotate even pages by x degree',
                        type=int, default=270)

    args = parser.parse_args()
    rotate_pdf(folder=args.folder,
               how={'all': args.all,
                    'odd': args.odd,
                    'even': args.even}
               )


if __name__ == '__main__':
    main()
