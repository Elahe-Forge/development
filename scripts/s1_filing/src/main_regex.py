
from preprocess import load_pdf, parse_html, clean_text
import pandas as pd
import re
from unicodedata import normalize

def clean_text(text):
    text = normalize("NFKD", text)
    text = text.replace('¬†', ' ')
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  
    text = text.replace('\xa0', ' ')            
    text = re.sub(r'\s+', ' ', text)            
    text = text.strip()                         
    return text



def main():

    df = pd.read_csv('../data/S-1.csv')

    for index, row in df.iterrows():
        
        html_url = row['Link']
        issuer = row['Issuer']
        
        # if issuer == "monday-com":
        # if issuer == "alumis" or issuer =="monday-com":
        if 1==1:
            print(issuer)


            html_texts = parse_html(html_url)
            html_texts = [str(node) for node in html_texts]
            # print(len(html_texts))
            html_texts_cleaned = clean_text(" ".join(html_texts))
            # for t in html_texts:
            #     print(t)

            # pattern = r"Securities and Exchange Commission on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s\d{1,2},\s\d{4}))"
            # pattern = r"Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s\d{1,2},\s\d{4}))"
            # pattern = r"(As\s+(filed\s+with|confidentially\s+submitted\s+to)\s+)?Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s\d{1,2},\s\d{4}))"
            # pattern = r"(As\s+(filed\s+with|confidentially\s+submitted\s+to)\s+)?Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s*\n*\s*\d{1,2}\s*\n*,\s*\n*\d{4}))"
            pattern = r"(As\s+(filed\s+with|confidentially\s+submitted\s+to)\s+)?Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s*\d{1,2}\s*,\s*\d{4}))"
            # pattern = r"(As\s+(filed\s+with|confidentially\s+submitted\s+to)\s+)?Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s+\d{1,2},\s+\d{4}))"

            matches = re.finditer(pattern, html_texts_cleaned)

            result = []
            date_part = None
            for match in matches:
                full_match = match.group(0)  # The full matched phrase with "Securities and Exchange Commission on"
                # date_part = match.group(1)
                date_part = match.group(3) if match.group(3) else match.group(4)
                start_pos, end_pos = match.span()  # Start and end positions
                result.append({
                    "full_match": full_match,
                    "date_part": date_part,
                    "start": start_pos,
                    "end": end_pos
                })

                print(result)
                
            cleaned_txt = clean_text(date_part) if date_part else ""
            print(cleaned_txt)
            df.at[index, 'date'] = cleaned_txt

        
            # Convert the cleaned text to a datetime object
            try:
                formatted_date = pd.to_datetime(cleaned_txt, errors='coerce')
                if pd.notnull(formatted_date):
                    # Format the date as MM/DD/YYYY
                    formatted_date = formatted_date.strftime('%m/%d/%Y')
                else:
                    formatted_date = ""
            except Exception as e:
                formatted_date = ""
    
            df.at[index, 'Cleaned Date'] = formatted_date

    df.to_csv('../data/S-1_with_results.csv', index=False, encoding='utf-8')

if __name__ == "__main__":
    main()

    




