import pandas as pd
import requests
import os
import pdfkit

def download_pdfs_from_csv(csv_file_path='../data/s1_lingo.csv', output_directory='../data'):

    df = pd.read_csv(csv_file_path)

    for index, row in df.iterrows():
        pdf_url = row['Link']
        pdf_name = row['Issuer']

        pdf_filename = os.path.join(output_directory, f'{pdf_name}.pdf')

        if os.path.exists(pdf_filename):
            print(f"File {pdf_filename} already exists. Skipping download.")
            continue

        try:
            headers = {'User-Agent': 'ela, elahe.paikari@forgeglobal.com'}
            # Send a HTTP GET request to fetch the PDF
            response = requests.get(pdf_url, headers=headers)
            response.raise_for_status()  # Check if the request was successful

            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type:
                # Save the PDF content to a file
                with open(pdf_filename, 'wb') as pdf_file:
                    pdf_file.write(response.content)
                print(f"Downloaded: {pdf_filename}")
            else:
                # If the content type is not PDF, save it as an HTML file for conversion
                error_filename = os.path.join(output_directory, f'{pdf_name}.html')
                with open(error_filename, 'wb') as error_file:
                    error_file.write(response.content)
                print(f"Warning: URL did not return a PDF. Content saved as {error_filename} for inspection.")

                # Convert the HTML file to a PDF
                pdfkit.from_file(error_filename, pdf_filename)
                print(f"Converted HTML to PDF: {pdf_filename}")    

            
            # Save the PDF content to a file
            with open(pdf_filename, 'wb') as pdf_file:
                pdf_file.write(response.content)

            print(f"Downloaded: {pdf_filename}")
                    
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {pdf_url}: {e}")

    return pdf_url, pdf_filename

