# Importing necessary libraries
import re
import ast
import time
import numpy as np
import pandas as pd
import datetime
import pickle
import csv

from IPython.display import display
from geopy.distance import geodesic
import missingno as msno
import matplotlib.pyplot as plt
import seaborn as sns
 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
import json
from bs4 import BeautifulSoup


def save_data(data, filename):
    # Saving DataFrame to CSV file
    data.to_csv(f"data/{filename}.csv", index=False)
    
def read_data(filename):
    df = pd.read_csv(f"data/{filename}.csv")
    return df

def parse_data_from_krisha(first_page, last_page):
    # Creating DataFrame to store data
    krisha_df = pd.DataFrame(columns=['name', 'information', 'address', 'price', 'owner'])

    # Creating WebDriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")  # Running in headless mode
    chrome_options.binary_location = "/Applications/Google Chrome for Testing"
    driver = webdriver.Chrome(options=chrome_options)

    # URL
    base_url = "https://krisha.kz/prodazha/kvartiry/astana/?page="

    # Iterating over pages
    for page_number in range(first_page, last_page):  
        url = base_url + str(page_number)
        driver.get(url)

        try:
            # Waiting for at least one element to load
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'a-card__title')))

            # Finding all elements on the page
            housing_complex_elements = driver.find_elements(By.CLASS_NAME, 'a-card')

            # Iterating over complex elements
            for complex_element in housing_complex_elements:
                # Extracting required data
                name = complex_element.find_element(By.CLASS_NAME, 'a-card__title').text.strip()
                information = complex_element.find_element(By.CLASS_NAME, 'a-card__text-preview').text.strip()
                address = complex_element.find_element(By.CLASS_NAME, 'a-card__subtitle').text.strip()
                price = complex_element.find_element(By.CLASS_NAME, 'a-card__price').text.strip()
                
                # Using BeautifulSoup to parse HTML inside complex_element
                soup = BeautifulSoup(complex_element.get_attribute('outerHTML'), 'html.parser')
                
                # Searching for elements with different types of advertisements
                complex_label = soup.find('div', class_='a-card__complex-label')
                label_default = soup.find('div', class_='label--default')
                label_yellow = soup.find('div', class_='label--yellow')
                label_transparent = soup.find('div', class_='label--transparent')
                
                # Determining the type of advertisement
                if complex_label:
                    owner = "Новостройка"
                elif label_default:
                    owner = "Риелтор"
                elif label_yellow:
                    owner = "Хозяин недвижимости"
                elif label_transparent:
                    owner = "Риелтор"
                else:
                    owner = "Неизвестно"

                # Storing data in DataFrame
                data = [name, information, address, price, owner]
                krisha_df = pd.concat([krisha_df, pd.DataFrame([data], columns=krisha_df.columns)], ignore_index=True)
                
        except Exception as e:
            print(f"An error occurred: {e}")

    # Closing the WebDriver
    driver.quit()

    
    return krisha_df


def preprocess_krisha_df(krisha_df):
    
    krisha_df = krisha_df.drop_duplicates()
    # Extracting complex name, house type, construction year, ceiling height, furniture info,
    # bathroom info, condition,  from 'information' column
    krisha_df['complex_name'] = krisha_df.information.str.extract(r'жил\. комплекс ([^,]+)')[0]
    krisha_df['complex_name'] = krisha_df['complex_name'].apply(text_unification)
    krisha_df['house_type'] = krisha_df.information.str.extract(r'(\w+ дом)')[0]
    krisha_df['house_type'] = krisha_df['house_type'].apply(lambda x: x if x in ['монолитный дом', 'кирпичный дом', 'панельный дом'] else None)
    krisha_df['in_pledge'] = krisha_df.information.apply(lambda x: 'В залоге' in x)
    krisha_df['construction_year'] = krisha_df.information.str.extract(r'(\d{4}) г\.п|(\d{4}) г\.п\.')[0].astype(int)

    def process_ceiling_height(info):
        height_match = re.search(r'потолки (\d+(\.\d+)?)м', info)
        if height_match:
            height = float(height_match.group(1))
            if 2 <= height <= 8:
                return height
        return None

    krisha_df['ceiling_height'] = krisha_df['information'].apply(lambda x: process_ceiling_height(x))
    krisha_df['furniture_info'] = krisha_df.information.str.extract(r'(\w+ мебели)' or r'меблирована ([^,.]+)')[0]
    krisha_df['bathroom_info'] = krisha_df.information.str.extract(r'санузел (\w+)')
    krisha_df['bathroom_info'] = krisha_df['bathroom_info'].apply(lambda x: x if x in ['раздельный', '2', 'совмещенный'] else None)
    krisha_df['condition'] = krisha_df.information.str.extract(r'состояние: ([^,]+)')[0]

    # Extracting area, room count, floor information from 'name' column
    krisha_df['area'] = krisha_df.name.str.extract(r'(\d+(\.\d+)?) м²')[0].astype(float)
    krisha_df['room_count'] = krisha_df.name.str.extract(r'(\d+)-комнатная')[0].astype(int)
    krisha_df['floor'] = krisha_df.name.str.extract(r'([^,]+) этаж')[0]

    # Dividing floor information into total floor count and apartment floor 
    krisha_df['floor_count'] = krisha_df.floor.str.extract(r'\/(\d{1,2})') 
    krisha_df['floor'] = krisha_df.floor.str.extract(r'(\d{1,2})/')
    # Extraction of the number from price and converting it to integer
    krisha_df['price'] = krisha_df.price.replace(r'\D', '', regex=True)

    # Extracting district from 'address' column                     
    krisha_df['district'] = krisha_df.address.str.extract(r'(р-н\s+\w+|\w+ р-н)')[0] 
    krisha_df['district'] = krisha_df['district'].apply(lambda x: 'Байконур р-н' if x=='р-н Байконур' else x)
    # This lambda function applies regex to remove district names and commas from addresses
    krisha_df['address'] = krisha_df['address'].apply(
        lambda x: re.sub(r'(?:р-н\s+\w+|\w+\s+р-н)', '', x).replace(',', ''))
    krisha_df['address'] = krisha_df['address'].astype(str)
    krisha_df['address'] = krisha_df['address'].apply(lambda x: x.split(' — ')[0] if ' — ' in x else x)

    return krisha_df


def parse_data_from_kn():
    
    # We are downloading data on constructed residential complexes.
    # Creating DataFrame to store information about constructed living complexes
    constructed_complex_df = pd.DataFrame(columns=['complex_name', 'city_district', 'address', 'price', 'developer', 'characteristics'])

    # Base URL for scraping
    base_url = "https://www.kn.kz/zhilye-kompleksy/search/astana?priceMin=&priceMax=&priceType=all&classes=&stage=built&search=&orderName=default&orderDirection=asc"

    # Looping through all pages 
    for page in range(1, 37):
        url = f"{base_url}&page={page}"
        
        # Sending a GET request to the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Finding all blocks with information about housing complexes
        complex_blocks = soup.find_all("div", class_="kn-px-20 kn-py-15 kn-fs-14 kn-lh-16")

        for complex_block in complex_blocks:
            
            # Extracting the link to the housing complex
            complex_link = complex_block.find("a", class_="kn-link")["href"]
            full_complex_link = f"https://www.kn.kz{complex_link}"

            # Sending a GET request to the housing complex link
            complex_response = requests.get(full_complex_link)
            complex_soup = BeautifulSoup(complex_response.content, "html.parser")

            # Extracting the name of the housing complex
            complex_name = complex_soup.find("h1", class_="kn-fs-24 kn-lh-24 kn-m-0").text.strip()

            # Extracting the city district
            city_district = complex_soup.select_one('.kn-mx-25 > div:nth-of-type(2)').text.strip()
            
            # Extracting the address
            address = complex_soup.find('div', class_='kn-lh-16 kn-my-25').find('div', class_='col').text.strip()

            # Extracting the price
            price_element = complex_soup.select_one(
                '.kn-lh-16.kn-my-25:nth-of-type(2) .kn-mb-10:nth-of-type(3)'
            )
            
            if price_element:
                price = price_element.text.strip()
            else:
                price_element = complex_soup.select_one(
                    '.kn-lh-16.kn-my-25:nth-of-type(2) .kn-mb-10:nth-of-type(4)'
                )

                if price_element:
                    price = price_element.text.strip()
                else:
                    price_element = complex_soup.select_one(
                        '.kn-lh-16.kn-my-25:nth-of-type(2) .kn-mb-10:nth-of-type(2)'
                    )

                    if price_element:
                        price = price_element.text.strip()
                    else:
                        price = None  

            # Extracting the developer
            developer_element = complex_soup.select_one('.kn-lh-16.kn-my-25:nth-of-type(4) > div:nth-of-type(2)')

            if developer_element:
                developer = developer_element.text.strip()
            else:
                developer = None
            
            # Extracting the block with characteristics
            characteristics_block = complex_soup.find("div", id="complex-feature")

            characteristics = {}
            css_class = "col-6 col-md-4"
            for characteristic in characteristics_block.find_all("div", class_=css_class):
                css_class_ ="kn-lh-16 kn-text-color-grey-6 kn-mb-15 kn-pl-10"
                name = characteristic.find("div", class_=css_class_).text.strip()
                value = characteristic.find("div", class_="kn-pl-10").find_next_sibling("div").text.strip()
                characteristics[name] = value
            
            # Saving the extracted data to the pre-created DataFrame
            data = [complex_name, city_district, address, price, developer, characteristics]
            data_df = pd.DataFrame([data], columns=constructed_complex_df.columns)
            constructed_complex_df = pd.concat([constructed_complex_df, data_df], ignore_index=True)


    # We are downloading data on under-construction residential complexes
    # Creating DataFrame to store information about under construction living complexes
    under_construction_complex_df = pd.DataFrame(columns=['complex_name', 'city_district', 'address','price', 'developer', 'characteristics'])

    # Base URL for scraping new housing complexes
    base_url =  "https://www.kn.kz/zhilye-kompleksy/search/astana?priceMin=&priceMax=&priceType=all&classes=&stage=form&search=&orderName=default&orderDirection=asc"

    # Looping through all pages of new housing complexes
    for page in range(1, 11):

        url = f"{base_url}&page={page}"
        
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Finding all blocks with information about new housing complexes
        complex_blocks = soup.find_all("div", class_="kn-px-20 kn-py-15 kn-fs-14 kn-lh-16")

        for complex_block in complex_blocks:
            
            # Extracting the link to the new housing complex
            complex_link = complex_block.find("a", class_="kn-link")["href"]
            full_complex_link = f"https://www.kn.kz{complex_link}"

            # Sending a GET request to the new housing complex link
            complex_response = requests.get(full_complex_link)
            complex_soup = BeautifulSoup(complex_response.content, "html.parser")

            # Extracting the name of the new housing complex 
            complex_name = complex_soup.find("h1", class_="kn-fs-24 kn-lh-24 kn-m-0").text.strip()

            # Extracting the city district
            city_district = complex_soup.select_one('.kn-mx-25 > div:nth-of-type(2)').text.strip()
            
            # Extracting the address
            address = complex_soup.find('div', class_='row g-0 kn-mb-20').find('div', class_='col-4').text.strip()
    
            # Extracting the price
            price_element = complex_soup.select_one(
                '.kn-lh-16.kn-my-25:nth-of-type(2) .kn-mb-10:nth-of-type(3)'
                )
            
            if price_element:
                price = price_element.text.strip()
            else:
                price_element = complex_soup.select_one(
                    '.kn-lh-16.kn-my-25:nth-of-type(2) .kn-mb-10:nth-of-type(4)'
                )
                if price_element:
                    price = price_element.text.strip()
                else:
                    price_element = complex_soup.select_one(
                        '.kn-lh-16.kn-my-25:nth-of-type(1) .kn-mb-10:nth-of-type(3)'
                    )
                    if price_element:
                        price = price_element.text.strip()
                    else:
                        price_element = complex_soup.select_one(
                            '.kn-lh-16.kn-my-25:nth-of-type(1) .kn-mb-10:nth-of-type(4)'
                        )
                        if price_element:
                            price = price_element.text.strip()
                        else:
                            price = None  

            # Extracting the developer
            developer_element = complex_soup.select_one('.kn-lh-16.kn-my-25:nth-of-type(4) > div:nth-of-type(2)')
            if developer_element:
                developer = developer_element.text.strip()
            else:
                developer_element = complex_soup.select_one('.kn-lh-16.kn-my-25:nth-of-type(3) > div:nth-of-type(2)')     
                if developer_element:
                    developer = developer_element.text.strip()
                else:
                    developer = None
            
            # Extracting the block with characteristics
            characteristics_block = complex_soup.find("div", id="complex-feature")

            characteristics = {}
            css_class = "col-6 col-md-4"
            for characteristic in characteristics_block.find_all("div", class_=css_class):
                css_class_ = "kn-lh-16 kn-text-color-grey-6 kn-mb-15 kn-pl-10"
                name = characteristic.find("div", class_=css_class_).text.strip()
                value = characteristic.find("div", class_="kn-pl-10").find_next_sibling("div").text.strip()
                characteristics[name] = value
            
            # Saving the extracted data to the pre-created DataFrame
            data = [complex_name, city_district, address, price, developer, characteristics]
            data_df = pd.DataFrame([data], columns=under_construction_complex_df.columns)
            under_construction_complex_df = pd.concat([under_construction_complex_df, data_df], ignore_index=True)

    # combine two tables into one and return it
    complex_df = pd.concat([constructed_complex_df, under_construction_complex_df], ignore_index=True)
    
    return complex_df


def preprocess_complex_df(complex_df):
    # Extracting complex name without "ЖК" word from "complex_name" column
    complex_df['complex_name'] = complex_df.complex_name.apply(lambda x: ' '.join(x.split(' ')[1:]))
    complex_df['complex_name'] = complex_df['complex_name'].apply(text_unification)
    # Convert the string representation of dictionaries to actual dictionaries using ast.literal_eval
    complex_df['characteristics'] = complex_df['characteristics'].apply(ast.literal_eval)

    # Use json_normalize to expand the dictionaries into separate columns
    normalized_data = pd.json_normalize(complex_df['characteristics'])

    # Add the new columns to the original DataFrame
    complex_df = pd.concat([complex_df, normalized_data], axis=1)

    # Drop the column containing the original dictionaries
    complex_df = complex_df.drop('characteristics', axis=1)

    # Drop unnecessary created features from characteristics
    complex_df = complex_df.drop(['Стены', 'Варианты отделки', 'Окна', 'Умный дом'], axis=1)

    # Dictionary for new column names in english 
    new_columns = {'Класс ЖК': 'complex_class', 'Высота потолков': 'ceiling_height', 
                'Отопление':'heating', 'Этажность':'floor_count', 'Паркинг':'parking', 
                'Лифт':'elevator', 'Технология строительства':'house_type'}

    # Rename new columns using the rename method
    complex_df.rename(columns=new_columns, inplace=True)
    
    return complex_df


def find_missing_complexes(krisha_df, complex_df):
    # Creating sets of unique complex names
    set_df = set(krisha_df['complex_name'].unique())
    set_complex_df = set(complex_df['complex_name'].unique())

    # finding the missing complex names in complex_df
    difference = set_df.difference(set_complex_df)

    print(f"Number of complexes from the complex_df that do not match with complexes in the krisha_df or absent: {len(difference)}")
    print(f"List of these complexes: {list(difference)}")
    
    
def text_unification(complex_name: str) -> str:
    """
    Normalize complex_name by converting it to lowercase and replacing hyphens with spaces.

    Args:
        complex name (str): The complex name to be normalized.
    
    Returns:
        str: The normalized and cleaned from hyphens complex name.
    """
        
    if isinstance(complex_name, str):
        complex_name = complex_name.lower()
        complex_name = complex_name.replace('-', ' ')
    return complex_name

    
def second_preprocess_complex_df(complex_df):
    # Create new residential complex 'kolsai' based on 'sharyn'
    selected_row_sharyn = complex_df[complex_df.complex_name == 'sharyn'].copy()
    selected_row_sharyn['complex_name'] = f"kolsai"
    complex_df = pd.concat([complex_df, selected_row_sharyn], ignore_index=True)

    # Create new residential complex 'mod.comfort' based on 'mod'
    selected_row_mod = complex_df[complex_df.complex_name == 'mod'].copy()
    selected_row_mod['complex_name'] = f"mod.comfort"
    complex_df = pd.concat([complex_df, selected_row_mod], ignore_index=True) 

    # Create new residential complex 'арай 1' based on 'арай 2'
    selected_row_arai_2 = complex_df[complex_df.complex_name == 'арай 2'].copy()
    selected_row_arai_2['complex_name'] = f"арай 1"
    complex_df = pd.concat([complex_df, selected_row_arai_2], ignore_index=True) 

    # Create new residential complex 'atlant unique' based on 'atlant'
    selected_row_atlant = complex_df[complex_df.complex_name == 'atlant'].copy()
    selected_row_atlant['complex_name'] = f"atlant unique"
    complex_df = pd.concat([complex_df, selected_row_atlant], ignore_index=True)

    # Create new residential complexes 'sezim qala.baqyt', 'sezim qala.baqyt towers', 'sezim qala.senim' based on 'sezim qala'
    new_complex_names = ['sezim qala.baqyt', 'sezim qala.baqyt towers', 'sezim qala.senim']
    for new_name in new_complex_names:
        selected_row_sezim = complex_df[complex_df.complex_name == 'sezim qala'].copy()
        selected_row_sezim['complex_name'] = new_name
        complex_df = pd.concat([complex_df, selected_row_sezim], ignore_index=True)
        
    # Create new residential complexes 'capital park.flowers', 'capital park.light', 'capital park.water' based on 'capital park'
    parks = ['flowers', 'light', 'water']
    for park in parks:
        selected_row_park = complex_df[complex_df.complex_name == 'capital park'].copy()
        selected_row_park['complex_name'] = f"capital park.{park}"
        complex_df = pd.concat([complex_df, selected_row_park], ignore_index=True)
        
    # Create new residential complexes for different seasons based on 'времена года'
    seasons = ['зима', 'осень', 'лето', 'весна']
    for season in seasons:
        selected_row_vremena = complex_df[complex_df.complex_name == 'времена года'].copy()
        selected_row_vremena['complex_name'] = f"времена года. {season}"
        complex_df = pd.concat([complex_df, selected_row_vremena], ignore_index=True)

    corrections_dict_for_complex_df = {
        'восток 1': 'восток (бахус)',
        'восток (grand invest)': 'восток 2022',
        'восток': 'восток 2009',
        'абай': 'абай на отырар   габдуллина',
        'абай (по победы/абая)': 'абай на победы   абая',
        'aibike': 'айбике',
        '7 я': '7я', 
        'baqyt premium (бахыт премиум)': 'baqyt premium',
        'запад': 'запад по ул. сарыарка',
        'запад (grand invest)': 'запад по ул. нажимеденова',
        'седьмой континент': '7 континент',
        'академия': 'академия на кургалжинском шоссе',
        'биiк шанырак': 'биик шанырак',
        'уркер (коттеджный городок)': 'уркер (кг)',
        'family village': 'family village (кг)',
        'комсомольский (nak)': 'комсомольский nak',
        'орынбор (nak)': 'орынбор',
        'статус (ул. домалак ана)': 'статус 2',
        '3 га': '3 гектара',
        'arman tau': 'арман тау',
        'aru qala': 'ару кала',
        'vita': 'greenline.vita',
        'terra': 'greenline.terra',
        'aqua': 'greenline.aqua',
        'aura': 'greenline.aura',
        'зеленый квартал': 'greenline.зеленый квартал',
        'asyl mura': 'greenline.asyl mura',
        'bi city tokyo': 'greenline.tokyo',
        'mod': 'mod.standard',
        'по е 16': 'елорда даму мжк по ул. е16',
        'байтурсын': 'елорда даму по байтурсынова',
        'по улы дала': 'елорда даму по улы дала',
        'астана': 'мжк астана',
        '5 звезд': '5 звёзд',
        'семь бочек': '7 бочек',
        'айсафи': 'aisafi',
        'акбулак таун': 'akbulak town',
        'ак дидар': 'aq didar',
        'ак жол': 'aq jol',
        'arman de luxe': 'arman deluxe',
        'club house': 'clubhouse',
        'king house': 'kinghouse',
        'eco park': 'ecopark',
        'гранд алатау': 'grand alatau',
        'жайсан ns': 'jaisan',
        'меридиан': 'meridian',
        's club': 'sclub',
        'seven house': 'seven',
        'view park': 'viewpark',
        'view park family': 'viewpark family',
        'абылай хан': 'абылайхан',
        'айнакол': 'айнаколь',
        'ак булак': 'акбулак nak',
        'акбулак 2': 'ак булак 2',
        'акбулак 3': 'ак булак 3',
        'акбулак': 'ак булак',
        'алтын шар': 'алтын шар 1',
        'астана санi': 'astana sani',
        'баскару': 'баскару 1',
        'гульдер': 'гулдер',
        'жетiген': 'жетиген',
        'инфинити': 'инфинити 1',
        'караван': 'караван 1',
        'за рекой': 'лея за рекой',
        'сказка': 'сказка по ул. сейфулина',
        'оркен de luxe': 'оркен де люкс',
        "апарт отель ye's астана": "апарт отель ye's astana",
        'zhana omyr': 'zhana omir'
    }

    # Apply the dictionary to the 'complex_name' column
    complex_df['complex_name'] = complex_df['complex_name'].map(corrections_dict_for_complex_df).fillna(complex_df['complex_name'])

    # Creating new data to fill in missing residential complexes in the complex_df
    new_data = [
        {'complex_name': 'the one', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Динмухамеда Кунаева, стр. 8а', 'year': '2024', 'developer': 'BAZiS-A','complex_class': 'премиум', 'ceiling_height': '3.55 м', 'house_type': 'монолитная', 'floor_count': '18', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'по тулебаева', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Тулебаева, 1/1', 'year': '2015', 'developer': 'Кокжар НС ТОО','complex_class': 'эконом', 'ceiling_height': '2.8 м', 'house_type': 'кирпичная','floor_count': '5', 'parking': 'надземный', 'elevator': 'нет', 'heating': 'центральное'},
        {'complex_name': 'зор табыс', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Мукан Толебаев, 25', 'year': '2021', 'developer': 'ЖСК Zor Tabys','complex_class': 'комфорт', 'ceiling_height': '2.8 м', 'house_type': 'монолитная','floor_count': '10', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'ferrum city', 'city_district': 'Астана, р-н Сарыарка', 'address': 'улица Е 882, 7', 'year': '2024', 'developer': 'Ferrum','complex_class': 'бизнес', 'ceiling_height': '3 м', 'house_type': 'монолитная', 'floor_count': '9 - 18', 'parking': 'надземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'апартаменты the st. regis astana', 'city_district': 'Астана, р-н Нура', 'address': 'просп. Кабанбай батыра, 1', 'year': '2017', 'developer': 'MG Development','complex_class': 'премиум', 'ceiling_height': '4 м', 'house_type': 'монолитная','floor_count': '2 - 10', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'dauletti qalashyq', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. А.Байтурсынулы, 47/1стр', 'year': '2024', 'developer': 'GBG','complex_class': 'бизнес', 'ceiling_height': '3 м', 'house_type': 'монолитная','floor_count': '9 - 18', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'астана сәні 2', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. А.Байтурсынова, 47', 'year': '2020', 'developer': 'MTS Company LTD','complex_class': 'комфорт', 'ceiling_height': '2.7 м', 'house_type': 'монолитная','floor_count': '9 - 11', 'parking': 'надземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'aq bastay', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Ташенова 10/2', 'year': '2018', 'developer': None, 'complex_class': 'премиум', 'ceiling_height': '3.3 м', 'house_type': 'кирпичная', 'floor_count': '5', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'отель дипломат', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Динмухамед Конаев, 29', 'year': '2006', 'developer': 'ASI','complex_class': 'премиум', 'ceiling_height': '3 м', 'house_type': 'кирпичная','floor_count': '10', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'черёмушки', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Туркестан, 14/1', 'year': '2016', 'developer': 'ПСК Клен','complex_class': 'бизнес', 'ceiling_height': '3 м', 'house_type': 'монолитная','floor_count': '5', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'норд', 'city_district': 'Астана, р-н Алматы', 'address': ' ул. Тауелсиздик, 14/1', 'year': '2008', 'developer': 'ЖСК Алматы','complex_class': 'эконом', 'ceiling_height': '2.7 м', 'house_type': 'кирпичная','floor_count': '9', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'на кенесары сембинова', 'city_district': 'Астана, р-н Байконур', 'address': 'ул. Кенесары 73', 'year': '2022', 'developer': 'Елорда Даму','complex_class': 'эконом', 'ceiling_height': '2.7 м', 'house_type': 'кирпичная','floor_count': '9', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'сказка по ул. байтурсынова', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Аманжол Болекпаев, 10/1', 'year': '2019', 'developer': None, 'complex_class': 'эконом', 'ceiling_height': '2.8 м', 'house_type': 'кирпичная','floor_count': '7', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'green garden', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Баян Сулу, 19', 'year': '2017', 'developer': 'ЖСК Алматы', 'complex_class': 'премиум', 'ceiling_height': '3.2 м', 'house_type': 'кирпичная', 'floor_count': '6', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'ala tau comfort', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. ​Байтурсынова, 20/2', 'year': '2023', 'developer': 'ТОО House Project','complex_class': 'комфорт', 'ceiling_height': '3 м', 'house_type': 'кирпичная','floor_count': '10', 'parking': 'надземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'новые черёмушки', 'city_district': 'Астана, р-н Нура', 'address': 'ул. Умай ана, 2', 'year': '2019', 'developer': 'ПСК Клен', 'complex_class': 'бизнес', 'ceiling_height': '3 м', 'house_type': 'кирпичная', 'floor_count': '6', 'parking': 'подземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'феникс', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Е-810, 2/21', 'year': '2024', 'developer': 'Полёт-М','complex_class': 'комфорт',  'ceiling_height': '2.9 м', 'house_type': 'кирпичная', 'floor_count': '9', 'parking': 'надземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'жубанова', 'city_district': 'Астана, р-н Байконур', 'address': 'ул. Ахмета Жубанова, 4', 'year': '2016', 'developer': 'Елорда Даму', 'complex_class': 'комфорт', 'ceiling_height': '2.7 м', 'house_type': 'монолитная', 'floor_count': '9', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'мкр самал', 'city_district': 'Астана, р-н Сарыарка', 'address': 'микрорайон Самал', 'year': '2004', 'developer': 'BAZiS-A','complex_class': 'комфорт', 'ceiling_height': '2.7 м', 'house_type': 'монолитная','floor_count': '16', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'лея за рекой', 'city_district': 'Астана, р-н Есиль', 'address': 'ул. Бухар жырау, 25/1', 'year': '2020', 'developer': 'Лея','complex_class': 'бизнес', 'ceiling_height': '3 м', 'house_type': 'монолитная','floor_count': '7 - 9', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'сарайшик', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Темирбек Жургенов, 27/1', 'year': '2016', 'developer': 'Алматыкурылыс', 'complex_class': 'эконом', 'ceiling_height': '2.7 м', 'house_type': 'кирпичная', 'floor_count': '5', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'happy land', 'city_district': 'Астана, р-н Нура', 'address': 'шоссе Коргалжын, 111/1 стр', 'year': '2024', 'developer': 'Uidomhome','complex_class': 'комфорт', 'ceiling_height': '2.7 м', 'house_type': 'кирпичная', 'floor_count': '5', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'денсаулык бакыт', 'city_district': 'Астана, р-н Алматы', 'address': 'Трасса Астана-Караганда, 23', 'year': '2018', 'developer': 'Денсаулык Бакыт', 'complex_class': 'эконом', 'ceiling_height':'2.7 м', 'house_type': 'монолитная', 'floor_count': '9', 'parking':'надземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'алтын булак', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Шарль де Голль, 18/1', 'year': '2018', 'developer': 'Астана Сервис Строй Монтаж', 'complex_class': 'комфорт', 'ceiling_height': '2.7 м', 'house_type': 'монолитная', 'floor_count': '5', 'parking': 'подземный', 'elevator': 'пассажирский и грузовой', 'heating': 'центральное'},
        {'complex_name': 'эльнара', 'city_district': 'Астана, р-н Алматы', 'address': 'ул. Янушкевича 1/2', 'year': '2008', 'developer': 'Жана Жол Курылыс', 'complex_class': 'эконом', 'ceiling_height': '2.7 м', 'house_type': 'монолитная', 'floor_count': '10', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
        {'complex_name': 'по 188 ой улице', 'city_district': 'Астана, р-н Сарыарка', 'address': 'ул. Косшыгулулы, 18', 'year': '2013', 'developer': 'Орал-дизайн-стройсервис', 'complex_class': 'эконом', 'ceiling_height': '2.7 м', 'house_type': 'кирпичная', 'floor_count': '7', 'parking': 'надземный', 'elevator': 'пассажирский', 'heating': 'центральное'},
    ]

    # Concatenate the existing complex_df dataframe with the new data stored in a DataFrame format
    complex_df = pd.concat([complex_df, pd.DataFrame(new_data)], ignore_index=True)

    indexes_to_change = complex_df[complex_df.house_type=='кирпичная, монолитно-каркасная'].index
    complex_df.loc[indexes_to_change, 'house_type'] = 'кирпичная'
    indexes_to_change = complex_df[complex_df.house_type=='монолитно-каркасная, кирпичная'].index
    complex_df.loc[indexes_to_change, 'house_type'] = 'кирпичная'
    indexes_to_change = complex_df[(complex_df.house_type=='иное') | (complex_df.house_type=='монолитно-каркасная')].index
    complex_df.loc[indexes_to_change, 'house_type'] = 'монолитная'
    indexes_to_change = complex_df[complex_df.house_type=='монолитная, монолитно-каркасная'].index
    complex_df.loc[indexes_to_change, 'house_type'] = 'монолитная'
    indexes_to_change = complex_df[complex_df.house_type=='монолитно-каркасная, монолитная'].index
    complex_df.loc[indexes_to_change, 'house_type'] = 'монолитная'
    complex_df.house_type = complex_df.house_type.apply(lambda x: 'монолитный дом' if x == 'монолитная' else 'кирпичный дом')
    
    indexes_to_change = complex_df[complex_df.parking=='подземный, надземный'].index
    complex_df.loc[indexes_to_change, 'parking'] = 'подземный'
    indexes_to_change = complex_df[complex_df.parking=='надземный, подземный'].index
    complex_df.loc[indexes_to_change, 'parking'] = 'подземный'

    complex_df.loc[39, 'year'] = '2022'
    complex_df.loc[5, 'complex_class'] = 'эконом'
    complex_df.loc[563, 'complex_class'] = 'эконом'
    complex_df.loc[60, 'complex_class'] = 'комфорт'
    complex_df.loc[108, 'complex_class'] = 'комфорт'
    complex_df.loc[859, 'complex_class'] = 'комфорт'
    complex_df.loc[859, 'ceiling_height'] = '2.7 м'
    complex_df.loc[1080, 'complex_class'] = 'комфорт'
    complex_df.loc[1080, 'ceiling_height'] = '2.7 м'
    complex_df.loc[1082, 'complex_class'] = 'комфорт'
    complex_df.loc[1082, 'ceiling_height'] = '3 м'
    complex_df.loc[1081, 'complex_class'] = 'эконом'
    complex_df.loc[1081, 'ceiling_height'] = '2.6 м'

    complex_df.loc[207, 'complex_class'] = 'комфорт'
    complex_df.loc[862, 'complex_class'] = 'бизнес'
    complex_df.loc[1083, 'complex_class'] = 'бизнес'
    complex_df.loc[1084, 'complex_class'] = 'бизнес'
    complex_df.loc[1085, 'complex_class'] = 'бизнес'

    complex_df.loc[878, 'complex_class'] = 'бизнес'
    complex_df.loc[45, 'complex_class'] = 'комфорт'
    complex_df.loc[39, 'complex_class'] = 'комфорт'

    complex_df.loc[121, 'complex_class'] = 'бизнес'
    complex_df.loc[1077, 'complex_class'] = 'комфорт'
    complex_df.loc[1077, 'ceiling_height'] = '2.7 м'
    complex_df.loc[898, 'complex_class'] = 'эконом'
    complex_df.loc[898, 'parking'] = 'надземный'

    complex_df.loc[117, 'complex_class'] = 'комфорт'
    complex_df.loc[1065, 'complex_class'] = 'комфорт'
    complex_df.loc[320, 'complex_class'] = 'эконом'
    complex_df.loc[534, 'complex_class'] = 'бизнес'
    complex_df.loc[875, 'complex_class'] = 'премиум'

    complex_df.loc[421, 'city_district'] = 'Астана, р-н Алматы'
    complex_df.loc[459, 'city_district'] = 'Астана, р-н Есиль'

    complex_df.loc[46, 'complex_class'] = 'комфорт'
    complex_df.loc[298, 'complex_class'] = 'эконом'
    complex_df.loc[343, 'complex_class'] = 'эконом'

    complex_df.loc[331, 'complex_class'] = 'комфорт'
    complex_df.loc[407, 'complex_class'] = 'комфорт'
    complex_df.loc[433, 'complex_class'] = 'комфорт'
    complex_df.loc[434, 'complex_class'] = 'комфорт'
    complex_df.loc[144, 'complex_class'] = 'комфорт'
    complex_df.loc[268, 'complex_class'] = 'бизнес'
    complex_df.loc[763, 'complex_class'] = 'бизнес'
    complex_df.loc[592, 'complex_class'] = 'бизнес'
    complex_df.loc[50, 'complex_class'] = 'бизнес'
    complex_df.loc[315, 'complex_class'] = 'бизнес'
    complex_df.loc[613, 'complex_class'] = 'комфорт'
    complex_df.loc[989, 'complex_class'] = 'комфорт'
    complex_df.loc[285, 'complex_class'] = 'комфорт'
    complex_df.loc[523, 'complex_class'] = 'комфорт'
    complex_df.loc[126, 'complex_class'] = 'комфорт'
    complex_df.loc[466, 'complex_class'] = 'комфорт'
    complex_df.loc[407, 'complex_class'] = 'комфорт'
    complex_df.loc[391, 'complex_class'] = 'комфорт'
    complex_df.loc[34, 'complex_class'] = 'комфорт'
    complex_df.loc[574, 'complex_class'] = 'эконом'

    complex_df.loc[122, 'ceiling_height'] = '2.73 м'
    complex_df.loc[334, 'ceiling_height'] = '2.7 м'
    complex_df.loc[792, 'ceiling_height'] = '2.7 м'
    complex_df.loc[793, 'ceiling_height'] = '3 м'
    complex_df.loc[808, 'ceiling_height'] = '3 м'
    complex_df.loc[1054, 'ceiling_height'] = '3 м'

    complex_df.loc[191, 'elevator'] = 'пассажирский'
    complex_df.loc[434, 'elevator'] = 'пассажирский и грузовой'
    complex_df.loc[542, 'elevator'] = 'пассажирский'
    complex_df.loc[1036, 'elevator'] = 'пассажирский'
    complex_df.loc[837, 'address'] = "Косшы, п. Косшы, в 200 м южнее ЖМ 'Лесная Поляна'"
    
    complex_df.loc[complex_df.complex_name == 'жайна', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'family town', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'орбита', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'памир', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'нурсая 2', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'орбита', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'формула успеха', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'жастар', 'complex_class'] = 'эконом'
    complex_df.loc[complex_df.complex_name == 'жастар 2', 'complex_class'] = 'эконом'
    complex_df.loc[complex_df.complex_name == 'жастар 3', 'complex_class'] = 'эконом'
    complex_df.loc[complex_df.complex_name == 'жастар 4', 'complex_class'] = 'эконом'
    complex_df.loc[complex_df.complex_name == 'нурсая', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'абай на победы   абая', 'complex_class'] = 'бизнес'
    complex_df.loc[complex_df.complex_name == 'окжетпес', 'complex_class'] = 'комфорт'  
    complex_df.loc[complex_df.complex_name == 'победа', 'complex_class'] = 'комфорт' 
    complex_df.loc[complex_df.complex_name == 'визит', 'complex_class'] = 'бизнес' 
    complex_df.loc[complex_df.complex_name == '7 континент', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'сказочный мир', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'радуга', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'лея за рекой', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'номад', 'complex_class'] = 'комфорт'
    complex_df.loc[complex_df.complex_name == 'лея комфорт', 'complex_class'] = 'комфорт'

    complex_df.loc[complex_df.complex_name == 'amsterdam', 'address'] = 'Улица Анет баба, 3'
    complex_df.loc[complex_df.complex_name == 'q life', 'address'] = 'Улица Роза Багланова, 3/1'
    complex_df.loc[complex_df.complex_name == 'sezim qala.senim', 'address'] = 'Проспект Туран, 55/7'
    complex_df.loc[complex_df.complex_name == 'sezim qala.baqyt towers', 'address'] = 'Улица Роза Багланова, 12/5 стр'
    complex_df.loc[complex_df.complex_name == 'sezim qala', 'address'] = 'Бигвилль "Sezim Qala"'
    complex_df.loc[complex_df.complex_name == 'sezim qala.baqyt', 'address'] = 'Проспект Туран, 55к'
    complex_df.loc[complex_df.complex_name == 'yrys', 'address'] = '​Трасса Астана-Караганда, 4/3'
    complex_df.loc[complex_df.complex_name == 'легенда', 'address'] = 'Легенда, жилой комплекс'
    complex_df.loc[complex_df.complex_name == 'grand victoria', 'address'] = "Жилой комплекс 'Grand Victoria'"
    complex_df.loc[complex_df.complex_name == 'victoria palace', 'address'] = "Район газовой аппаратуры"
    complex_df.loc[complex_df.complex_name=='скандинавия', 'address'] = "Жилой клуб 'Скандинавия'"
    complex_df.loc[complex_df.complex_name == 'курылтай', 'address'] = 'Микрорайон 5Б, 88/1'
    complex_df.loc[complex_df.complex_name == 'balgyn', 'address'] = 'Улица Лесная поляна, 29/1'
    complex_df.loc[complex_df.complex_name == 'family house', 'address'] = 'Микрорайон 5Б, 88/1'
    complex_df.loc[complex_df.complex_name == 'самрук байтерек', 'address'] = '016-й учетный квартал, 9113 стр'
    complex_df.loc[complex_df.complex_name == 'по ракымова', 'address'] = 'Улица Шокан Уалиханов, 25/2'
    complex_df.loc[complex_df.complex_name == 'ак булак 3', 'address'] = 'Переулок Тасшокы, 3'
    complex_df.loc[complex_df.complex_name == 'iconic', 'address'] = '​Улица Кадыргали Жалайыри, 4'
    complex_df.loc[complex_df.complex_name == 'capital park', 'address'] = 'Улица Керей-Жанибек хандар, 50/1'
    complex_df.loc[complex_df.complex_name == 'capital park.water', 'address'] = 'Улица Керей-Жанибек хандар, 50/3'
    complex_df.loc[complex_df.complex_name == 'уркер (кг)', 'address'] = 'Коттеджный городок "Уркер"'
    complex_df.loc[complex_df.complex_name == 'onyx comfort', 'address'] = 'Onyx Comfort, жилой комплекс'
    complex_df.loc[complex_df.complex_name == 'river city', 'address'] = 'River City, жилой комплекс'
    complex_df.loc[complex_df.complex_name == 'астана сәні 2', 'address'] = 'Улица Ахмет Байтурсынулы, 47'
    complex_df.loc[complex_df.complex_name == 'astana sani', 'address'] = 'Улица Ахмет Байтурсынулы, 53'


    complex_df['elevator'] = complex_df['elevator'].apply(lambda x: 'нет' if pd.isna(x) else x)
    complex_df['elevator'] = complex_df['elevator'].apply(lambda x: 'пассажирский и грузовой' if x=='пассажирский и грузовой, пассажирский' else x)
    complex_df['elevator'] = complex_df['elevator'].apply(lambda x: 'пассажирский и грузовой' if x=='пассажирский, пассажирский и грузовой' else x)
    complex_df['elevator'] = complex_df['elevator'].apply(lambda x: 'пассажирский' if x=='пассажирский, нет' else x)
    complex_df['parking'] = complex_df['parking'].apply(lambda x: 'нет' if pd.isna(x) else x)
    complex_df['year'] = complex_df['year'].str.extract(r'(\b\d{4}\b)')[0].astype(int)
    complex_df['ceiling_height'] = complex_df['ceiling_height'].str.extract(r'(\d+\.\d+|\d+)').astype(float)
    complex_df['district'] = complex_df['city_district'].str.replace('Астана, ', '')

    replace_dict = {
        'р-н Алматы': 'Алматы р-н',
        'р-н Есиль': 'Есильский р-н',
        'р-н Нура': 'Нура р-н',
        'р-н Сарыарка': 'Сарыарка р-н',
        'р-н Байконур': 'Байконур р-н',
        'р-н Косшы': 'Косшы р-н'
    }
    complex_df['district'] = complex_df['district'].replace(replace_dict)
    complex_df = complex_df.drop(['developer', 'heating', 'city_district'], axis=1)

    # Функция для разделения значения floor_count на min_floor_count и max_floor_count
    def split_floor_count(value):
        floors = value.split(' – ')
        if len(floors) == 2:
            return int(floors[0]), int(floors[1])
        else:
            floor = int(value.split(' - ')[0])
            return floor, floor

    # Разделение значения floor_count на min_floor_count и max_floor_count
    complex_df[['min_floor_count', 'max_floor_count']] = pd.DataFrame(complex_df['floor_count'].apply(split_floor_count).tolist())

    # Удаление исходного признака floor_count
    complex_df.drop(columns=['floor_count'], inplace=True)
    
    return complex_df

def second_preprocess_krisha_df(krisha_df):
        
    # Update complex names based on house types
    # Update complex name to 'восток 2009' for monolithic houses in 'восток'
    vostok_09 = krisha_df.query("complex_name.str.contains('восток') and house_type=='монолитный дом'").index
    krisha_df.loc[vostok_09, 'complex_name'] = 'восток 2009'

    # Update complex name to 'восток 2022' for brick houses in 'восток'
    vostok_22 = krisha_df.query("complex_name.str.contains('восток') and house_type=='кирпичный дом'").index
    krisha_df.loc[vostok_22, 'complex_name'] = 'восток 2022'

    # Update complex name to 'восток 2009' for houses with null house types in 'восток'
    vostok_22 = krisha_df.query("complex_name.str.contains('восток') and house_type.isnull()").index
    krisha_df.loc[vostok_22, 'complex_name'] = 'восток 2009'

    # Dictionary containing corrections for the 'complex_name' column in krisha_df
    corrections_dict_for_krisha_df = {  
        'озен': 'ozen',
        'кок жайлау': 'кок жайлау',
        'коркем tower': 'коркем tоwer',
        'аль фараби 20': 'аль фараби 2',
        'сауран 3': 'сауран',
        'сауран   4': 'сауран',
        'aviator ii': 'aviator 2',
        'armantau comfort ii': 'armantau comfort',
        'есиль (бокейхана': 'есиль',
        'жилой дом по ул. айнакол': 'по айнакол',
        'целиноград − 2': 'целиноград',
        'целиноград − 3': 'целиноград',
        'целиноград − 4': 'целиноград',
        'камал 2': 'камал',
        'камал 3': 'камал',
        'камал 4': 'камал',
        'нипи 2': 'нипи',
        'greenline.asyl mura jubanov': 'greenline.asyl mura',
        'greenline.headliner exclusive': 'headliner exclusive',
        'мжк райымбек': 'raiymbek',
        'europe рalace i': 'europe palace',
        'europe рalace ii': 'europe palace',
        'highvill ishim c': 'highvill ishim',
        'sharyn 2': 'sharyn',
        'kolsai 2': 'kolsai',
        'sultan apartaments': 'sultan apartments',
        'vip городок саранда': 'vip городок saranda',
        'саранда': 'vip городок saranda',
        'махаббат 2': 'махаббат',
        'абылайхан 2': 'абылайхан',
        'авицена элит': 'авиценна элит',
        'адам арманы': 'adam armany',
        'алтын саулет': 'altyn saulet',
        'алтын ұя': 'алтын уя',
        'апарт отель yes astana': "апарт отель ye's astana",
        'арлан': 'arlan',
        'бахыт премиум': 'baqyt premium',
        'астана сәні': 'astana sani',
        'асыл тау': 'assyl tau',
        'атамура': 'atamura',
        'бадана': 'badana',
        'бигвилль поколение': 'поколение',
        'бозбиік': 'bozbiik',
        'бронкс': 'bronx',
        'бухар жырау': 'buqar jyray',
        'вена': 'vienna',
        'гималаи': 'гималай',
        'городской романс': 'французский квартал',
        'градокомплекс 4': 'градокомплекс 3',
        'дельфин 2': 'дельфин',
        'деңсаулық бақыт': 'денсаулык бакыт',
        'дива': 'diva',
        'достар': 'достар 1',
        'ельтай': 'елтай',
        'жагалау 2': 'жагалау 3',
        'зам зам': 'zam zam',
        'кулан 2': 'кулан',
        'лея плюс': 'лея',
        'либерти': 'liberty',
        'лондон': 'london',
        'магистральный 1': 'магистральный',
        'магистральный 2': 'магистральный',
        'магистральный 3': 'магистральный',
        'мади': 'madi',
        'меретти': 'меррити',
        'меркурий 2': 'меркурий',
        'мжк отырар': 'отырар',
        'нурсая бонита': 'нурсая 2',
        'орбита 2': 'орбита',
        'отан 2': 'отан',
        'aylet' : 'аулет',
        'самгау 2': 'самгау',
        'сан сити': 'sun city',
        'сармат 1': 'сармат',
        'сармат 2': 'сармат',
        'сатти 7': 'сатты 7',
        'толенды': 'коктал',
        'турсын астана 2': 'турсын астана',
        'nuraly apartments': 'the nurali apartments',
        'умай': 'umai',
        'ясин': 'yasin',
        'expo new life 2': 'expo new life',
        'trinity': 'capital park.flowers',
    }
    
    # Map the corrections dictionary to the 'complex_name' column in complex_df
    krisha_df['complex_name'] = krisha_df['complex_name'].map(corrections_dict_for_krisha_df).fillna(krisha_df['complex_name'])
    return krisha_df


def geocode_2gis(address):
    address = address + ", Астана"
    api_key = '031aa401-ce07-402c-95ed-23f70fc51f24' 
    #api_key = 'ed9415cf-b4fd-4bc5-98b9-9da7e3ee9908' #'dbfc2ea8-0262-4ef3-acb2-d0a46adf9557'
    url = f'https://catalog.api.2gis.com/3.0/items/geocode?q={address}&fields=items.point&key={api_key}'

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad response status
        data = response.json()

        if 'result' in data:
            result = data['result']
            if result['total'] > 0:
                item = result['items'][0]
                coordinates = item['point']
                return f"({coordinates['lat']}, {coordinates['lon']})"
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching or decoding JSON: {e}")
    return None


schools_coord_dict = {
    'Бәсіре переулок, 2, 2 этаж': (51.185095, 71.330193),
    'Ақкербез, 10': (51.148614, 71.408842),
    'Бөгенбай батыр проспект, 32/2, 2 этаж': (51.174351, 71.40896),
    'Озбек Али Жаныбек, 30, 2 этаж': (51.133087, 71.51445),
    'Жаһанша Досмұхамедұлы, 2': (51.180906, 71.47141),
    'Бориса Ерзаковича, 20, 2 этаж': (51.180223, 71.367633),
    'Сарайшық, 7/1': (51.136013, 71.428764),
    'Е-624, 8': (51.03923, 71.430131),
    'Кенен Әзірбаев, 39, 2 этаж': (51.126429, 71.494442),
    'Майлина, 16/3': (51.144977, 71.475581),
    'Асқар Тоқпанов, 40, 3 этаж': (51.145374, 71.451735),
    'Иманова, 40, 2 этаж': (51.161506, 71.453804),
    'А 135, 7, 2 этаж': (51.124163, 71.611552),
    'Қамысты, 7, 2 этаж': (51.199447, 71.454819),
    'Халел Досмұхамедұлы, 51': (51.139449, 71.421282),
    'Әміре Қашаубаев, 28, 1 этаж': (51.11551, 71.243237),
    'Маяковского, 3/2, 2 этаж': (51.145683, 71.56385),
    'Айғаным, 2': (51.139438, 71.403665),
    'Кенесары, 93/1, 2 этаж': (51.162751, 71.467509),
    'Шығанақ, 7, 3 этаж': (51.158387, 71.406872),
    'Евгения Брусиловского, 4/3, 2 этаж': (51.160311, 71.456362),
    'Қараменде би Шақаулы, 5/1, 2 этаж': (51.17231, 71.369181),
    'Егемен Қазақстан, 10, 2 этаж': (51.169768, 71.455007),
    '247-я, 2, 2 этаж': (51.112273, 71.649066),
    'Абай проспект, 86/1, 2 этаж': (51.164434, 71.463859),
    '50/3, 2 этаж': (51.11153, 71.41429),
    'Жумабека Ташенова, 9/4, 2 этаж; 2 корпус': (51.154049, 71.440049),
    'Телжан Шонанұлы, 47, 2 этаж': (51.196118, 71.432177),
    'Түркістан, 12/1, 2 этаж': (51.110774, 71.428313),
    'Қошке Кемеңгерұлы, 10а, 2 этаж': (51.206681, 71.397385),
    'А-98, 2, 2 этаж': (51.124048, 71.489445),
    'Бейбітшілік, 75а, 2 этаж': (51.187009, 71.413827),
    'Айбырая Алтынсарина, Абай Кұнанбайұлы, 31, 2 этаж': (51.247942, 71.252027),
    'Николая Хлудова, 1/1, 2 этаж': (51.146464, 71.433921),
    'Карасай батыра, 31/2': (51.199053, 71.389208),
    'Алии Молдагуловой, 21': (51.091408, 71.721893),
    'Ардагерлер, 13, 2 этаж': (51.182051, 71.341128),
    'Иманжүсiп Құтпанов, 16а, 2 этаж': (51.191849, 71.415625),
    'Малика Габдуллина, 8, 2 этаж': (51.160025, 71.433806),
    'Шонанулы, 45': (51.195977, 71.431179),
    'Әліби Жангелдин, 1, 2 этаж': (51.173111, 71.408391),
    'Иманак, 9/1, 2 этаж': (51.150242, 71.56218),
    'Абылай Хана проспект, 8/1, 2 этаж; 1 корпус': (51.158037, 71.472773),
    'Мәскеу, 38, 2 этаж': (51.182142, 71.418538),
    'Александра Затаевича, 9/7, 2 этаж': (51.188962, 71.402823),
    'Бейімбет Майлин, 3/1, 3 этаж': (51.143339, 71.464115),
    'Әліби Жангелдин, 28, 3 этаж': (51.173492, 71.421442),
    'Кенен Әзірбаев, 41, 2 этаж': (51.12692, 71.496183),
    'Ахмета Жубанова, 2, 3 этаж': (51.158091, 71.457946),
    '38-я, 2, 2 этаж': (51.101383, 71.455812),
    'Петрова, 3/1, 2 этаж': (51.150933, 71.462947),
    'Орынбор, 20, 2 этаж': (51.106277, 71.439497),
    'Сарытогай, 9, 2 этаж': (51.043686, 71.426601),
    'Степана Кубрина, 22/1': (51.170427, 71.404754),
    'Сырым батыр, 105, 2 этаж': (51.128878, 71.252357),
    'Кенен Әзірбаев, 2/1, 2 этаж': (51.12714, 71.505779),
    'Дінмұхамед Қонаев, 35': (51.130544, 71.436021),
    '638-я, 2, 3 этаж': (51.135472, 71.288601),
    'Абылай Хана проспект, 23/1, 2 этаж': (51.157355, 71.4857),
    'Абай проспект, 17, 1 этаж': (51.166813, 71.41115),
    'Республики проспект, 12/5, 2 этаж': (51.161856, 71.43043),
    'Міржақып Дулатов, 176/1, 2 этаж': (51.205199, 71.366701),
    '37 переулок, 3/1': (51.145961, 71.496347),
    'Ақан сері, 42/3, 2 этаж': (51.183476, 71.375421),
    'Әлия Молдағұлова, 35': (51.18713, 71.418162),
    'Мәскеу, 28а, 2 этаж; 2 корпус': (51.180598, 71.40711),
    'Сауран, 20/1, 2 этаж': (51.111828, 71.418486),
    'Ыбырай Алтынсарин, 12, 2 этаж': (51.191022, 71.413618),
    'Ақмешіт, 5/1, 2 этаж': (51.119041, 71.42263),
    'Жанкент, 23': (51.139367, 71.507267),
    'Кравцова, 2/3, 2 этаж': (51.156544, 71.439968),
    'Әлихан Бөкейхан, 4/1, 2 этаж': (51.118588, 71.438712),
    'Мәңгілік Ел проспект, 82, 3 этаж': (51.069888, 71.421181),
    'Алматы, 13/1, 2 этаж': (51.117505, 71.431305),
    'Александр Герцен, 84/1, 2 этаж': (51.198014, 71.366194),
    'Желтоксан, 31, 2 этаж': (51.174327, 71.413361),
    'Темірбек Жүргенов, 30/1, 3 этаж': (51.12401, 71.506949),
    'Карасай батыра, 31/1, 2 этаж': (51.198333, 71.389492),
    'Дауылпаз, 1, 2 этаж': (51.130598, 71.463349),
    'Қыз Жібек, 40а, 2 этаж': (51.143472, 71.387507),
    'Султанмахмуда Торайгырова, 11, 3 этаж': (51.175699, 71.426556),
    'Қаныш Сәтбаев, 8/1, 2 этаж': (51.154849, 71.465843),
    'ықылас Дүкенұлы, 32, 2 этаж': (51.180018, 71.432283),
    'ықылас Дүкенұлы, 18, 2 этаж': (51.179168, 71.426459),
    'Ак-булак-2, 11, 2 этаж': (51.145506, 71.447149),
    'Щорса, 37, 1-3 этаж': (51.173293, 71.399793),
    'Е 12, 4, 2 этаж': (51.127915, 71.377335),
    'Тұмар ханым, 24, 2 этаж': (51.143464, 71.393534),
    'Е 12, 6, 2 этаж': (51.127848, 71.37821),
    '61-й проезд, 6/1, 2 этаж': (51.043337, 71.432713),
    '25-я, 10/1, 2 этаж': (51.103019, 71.426455),
    'Жұбан ана, 10, 3 этаж': (51.145166, 71.402482),
    'Желтоксан, 28/1, 2 этаж': (51.174365, 71.41504),
    'Шертер, 5, 3 этаж': (51.132251, 71.46436),
    'Гейдар Әлиев, 2/4, 3 этаж': (51.150109, 71.451229),
    'Мағжан Жұмабаев проспект, 1/1, 2 этаж': (51.154971, 71.476235),
    'А 195, 1, 2 этаж': (51.12893, 71.492398),
    'Ақмешіт, 5/2, 2 этаж': (51.117742, 71.422364),
    'Сарыарқа проспект, 50': (51.180336, 71.405539),
    'Қыз Жібек, 30, 2 этаж': (51.141143, 71.391383),
    'Шәймерден Қосшығұлұлы, 13/3, 2 этаж': (51.167473, 71.386169),
    'Петрова, 17/1, 2 этаж; 2 корпус': (51.15079, 71.471225),
    'Республики проспект, 21/1, 4 этаж': (51.163725, 71.426343),
    'генерал Сабыр Рақымов, 33, 2 этаж': (51.165315, 71.437042),
    'Мәскеу, 29/4, 2 этаж; 1 корпус': (51.18316, 71.406273),
    'Тәуелсіздік проспект, 14/3, 2 этаж': (51.147894, 71.462027),
    'Кенен Әзірбаев, 12/1, 2 этаж': (51.125166, 71.498664),
    'Алматы, 4, 2 этаж': (51.117197, 71.415198),
    'Мухтара Ауэзова, 43/2, 2 этаж': (51.180811, 71.418732),
    'Біржан сал, 6/1, 2 этаж': (51.192332, 71.409419),
    'Керей, Жәнібек хандар, 30': (51.111364, 71.437407),
    'Айнакөл, 66/1, 2 этаж': (51.128703, 71.488754),
    'микрорайон Жагалау, 3, 2 этаж': (51.135322, 71.36591),
    'Петрова, 7/2, 2 этаж': (51.150206, 71.465366),
    'Карасай батыра, 3, 2 этаж': (51.195062, 71.402013),
    'Әліби Жангелдин, 15, 2 этаж': (51.174232, 71.420896),
    'Күйші Дина, 38/1, 2 этаж': (51.155232, 71.491779),
    'Қобыз, 32/1, 2 этаж': (51.134456, 71.519124),
    'Қайрат Рысқұлбеков, 8/3, 2 этаж': (51.15475, 71.500761),
    'Тулкибас, 58': (51.143324, 71.495592),
    'Темірбек Жүргенов, 18/2': (51.114076, 71.502729),
    'Кенжебек Күмісбеков, 12/1, 2 этаж': (51.170425, 71.400108),
    'Бурабай, 40, 2 этаж': (51.151525, 71.518474),
    '187-я, 20/6, 2 этаж': (51.173084, 71.382674)
    }

kindergartens_coord_dict = {
    'Ул. Косалка, д. 28': (51.140075, 71.485026),
    'Пр-кт Туран, д. 14': (51.142663, 71.412659),
    'Ул. Ыбрая Алтынсарина, д. 12': (51.191022, 71.413618),
    'Ул. Кенена Азербаева, д. 41': (51.12692, 71.496183),
    'Пр-кт Богенбай батыра, д. 32, корп. 2': (51.174351, 71.40896),
    'Пр-кт Богенбай батыра, д. 19, корп. 2': (51.17633, 71.401737),
    'Ул. Ыкылас Дукенулы, д. 32': (51.180018, 71.432283),
    'Ул. Жангельдина, д. 1': (51.173111, 71.408391),
    'Ул. Сабира Рахимова, д. 22': (51.162188, 71.439184),
    'Пр-кт Абая, д. 95/1': (51.167307, 71.462254),
    'Ул. Косалка, д. 24': (51.139862, 71.484219),
    'Ул. А 195, д. 1': (51.12893, 71.492398),
    'Ул. Карасай батыра, д. 3': (51.195062, 71.402013),
    'Ул. Романтиков, д. 21': (51.144392, 71.454628),
    'Ул. Желтоксан, д. 48': (51.180711, 71.412639),
    'Ул. Александра Затаевича, д. 16, корп. 1': (51.190502, 71.404555),
    'Ул. Коксай, д. 1, корп. 1': (51.110487, 71.217157),
    'Ул. Челюскинцев, д. 90': (51.167854, 71.406261),
    'пр-кт Абылай Хана, д. 8, корп. 1': (51.158037, 71.472773),
    'ул. Габдуллина, д. 8': (51.160025, 71.433806),
    'ул. Шонанулы, д. 45': (51.195977, 71.431179),
    'ул. Акмолинская, д. 3': (51.109965, 71.216906),
    'ул. Халел Досмухамедулы, д. 33': (51.141212, 71.422396),
    'ул. Жумабека Ташенова, д. 21, корп. 1': (51.154217, 71.448859),
    'ул. Айман-Шолпан, д. 13': (51.140398, 71.402021),
    'ул. Кокарал, д. 12': (51.1317, 71.525029),
    'ул. Желтоксан, д. 31': (51.174327, 71.413361),
    'ул. Куйши Дина, д. 31': (51.152313, 71.485413),
    'ул. Алматы, д. 6': (51.116412, 71.4212),
    'ул. Иманжусипа Кутпанова, д. 16/а': (51.191849, 71.415625),
    'ул. Карасай батыра, д. 31, корп. 1': (51.198333, 71.389492),
    'ул. Конституции, д. 40': (51.195784, 71.393903),
    'ул. Лепсы, д. 59': (51.149147, 71.525912),
    'пр-кт Шакарима Кудайбердиулы, д. 2, корп. 1': (51.163039, 71.475435),
    'ул. Бейимбет Майлина, д. 16, корп. 3': (51.144977, 71.475581),
    'ул. Желтоксан, д. 28, корп. 1': (51.174365, 71.41504),
    'пр-кт Магжана Жумабаева, д. 1, корп. 1': (51.154971, 71.476235),
    'аул Караоткель, ул. Мустафа Шокай, д. 7': (51.123356, 71.217755),
    'ул. Кенжебека Кумисбекова, д. 12, корп. 1': (51.170425, 71.400108),
    'ул. Брусиловского, д. 4, корп. 3': (51.160311, 71.456362),
    'пр-кт Мангилик Ел, д. 22, корп. 2': (51.11408, 71.436805),
    'ул. Московская, д. 38': (51.182142, 71.418538),
    'ул. Герцена, д. 84': (51.198014, 71.366194),
    'ул. Жангельдина, д. 15': (51.174232, 71.420896),
    'ул. Петрова, д. 3, корп. 1': (51.151764, 71.463992),
    'ул. Московская, д. 28': (51.180598, 71.40711),
    'пр-кт Абылай Хана, д. 28, корп. 1': (51.154045, 71.483381),
    'ул. Шыганак, д. 7': (51.158387, 71.406872),
    'ул. Кошкарбаева, д. 33': (51.165315, 71.437042),
    'пр-кт Бауржана Момышулы, д. 28, корп. 12': (51.146364, 71.5015),
    'ул. Московская, д. 29, корп. 4': (51.18316, 71.406273),
    'ул. Сатпаева, д. 8, корп. 1': (51.151712, 71.470595),
    'ул. Петрова, д. 17, корп. 1': (51.15079, 71.471225),
    'ул. Иманбаевой, д. 16, оф. 57': (51.167922, 71.434146),
    'ул. Шонанулы, д. 47': (51.196118, 71.432177),
    'пер. Басире, д. 2': (51.185095, 71.330193),
    'пр-кт Женис, д. 41, корп. 2': (51.177208, 71.408317),
    'ул. Биржан Сала, д. 6, корп. 1': (51.192332, 71.409419),
    'ул. 187-я, д. 20, корп. 6': (51.173084, 71.382674),
    'ул. Тумар Ханым, д. 24': (51.143464, 71.393534),
    'ул. Кенесары, д. 93, корп. 1': (51.162751, 71.467509),
    'ул. Айнакол, д. 66, корп. 1': (51.128703, 71.488754),
    'пр-кт Тауелсыздык, д. 14, корп. 3': (51.147678, 71.459786),
    'ул. 24-я, д. 20': (51.106277, 71.439497),
    'ул. Камысты, д. 7': (51.199447, 71.454819),
    'ул. 188-я, д. 3, корп. 1': (51.167308, 71.392195),
    'ул. 247-я, д. 2': (51.112273, 71.649066),
    'ул. Кеменгерулы, д. 10': (51.206258, 71.397518),
    'ул. Жангельдина, д. 28': (51.173492, 71.421442),
    'ул. Александра Кравцова, д. 2, корп. 3': (51.156544, 71.439968),
    'пер. Минский, д. 4': (51.164955, 71.463493),
    'ул. Маяковского, д. 3, корп. 2': (51.145683, 71.56385),
    'ул. 188-я, д. 13, корп. 3': (51.167473, 71.386169),
    'пр-кт Республики, д. 21, корп. 1': (51.163725, 71.426343),
    'ул. Айдархана Турлыбаева, д. 13': (51.181694, 71.367934),
    'ул. Кайрата Рыскулбекова, д. 8': (51.155506, 71.498814),
    'ул. 167-я, д. 5, корп. 1': (51.10991, 71.217742),
    'ул. Ыкылас Дукенулы, д. 32': (51.180018, 71.432283),
    'пр-кт Богенбай батыра, д. 32, корп. 2': (51.174351, 71.40896),
    'ул. Дауылпаз, д. 1': (51.130598, 71.463349),
    'ул. Ардагерлер, д. 13': (51.182051, 71.341128)
    }

# Counting the number of nearby places
def count_places_within_radius(places_dict, complex_coordinates, radius):
   
    if places_dict == 'school':
        places_dict = schools_coord_dict
                
    elif places_dict == 'kindergarten':
        places_dict = kindergartens_coord_dict
            
    else:
        raise ValueError("Invalid places_dict argument. It should be 'school' or 'kindergarten'.")

    count = 0
    for place_coordinates in places_dict.values():
        distance = geodesic(complex_coordinates, place_coordinates).meters
        if distance <= radius:
            count += 1
    
    return count


# Checking if there is a park within 1 km radius
def checking_park(coordinates, radius):
    
    parks_coord_dict = {
    'Парк Президентский': (51.106349, 71.477572),
    'Парк Ғашықтар': (51.131764, 71.409002),
    'Парк им. Б. Момышулы': (51.131779, 71.456687),
    'Парк Времена года': (51.15173, 71.432224),
    'Триатлон Парк Астана': (51.13593, 71.449809),
    'Центральный парк культуры и отдыха «Столичный»': (51.156264, 71.419961),
    'Парк Арай': (51.134873, 71.437905),
    'Сквер Президентский': (51.166511, 71.417352),
    'Парк Жеруйык': (51.146082, 71.488548),
    'Шахматный парк': (51.164953, 71.42666),
    'Парк им. Ж. Жабаева': (51.151498, 71.445536),
    'Парк Студенческий': (51.155554, 71.46258),
    'Парк Пушкинский': (51.159982, 71.470155),
    'Парк Афганской войны': (51.157236, 71.477074),
    'Площадь Городская': (51.165511, 71.421089),
    'Площадь Защитников Отечества': (51.153045, 71.457329)
    }

    for park_coordinates in parks_coord_dict.values():
        distance = geodesic(coordinates, park_coordinates).meters
        if distance <= radius:
            return True
        
    return False  

    
def process_and_clean_data(merged_df):
    
    merged_df['coordinates'] = merged_df['coordinates_2gis'].combine_first(merged_df['coordinates_2gis_complex'])
    merged_df['ceiling_height'] = merged_df['ceiling_height'].combine_first(merged_df['ceiling_height_complex'])
    merged_df['house_type'] = merged_df['house_type_complex'].combine_first(merged_df['house_type'])
    merged_df['district'] = merged_df['district_complex'].combine_first(merged_df['district'])
    merged_df['address'] = merged_df['address'].combine_first(merged_df['address_complex'])
    
    # Удаление вторых не главных столбцов
    merged_df = merged_df.drop(['coordinates_2gis_complex', 'coordinates_2gis', 'ceiling_height_complex', 'house_type_complex', 'year', \
                                'district_complex', 'address_complex', 'full_address', 'max_floor_count', 'min_floor_count'], axis=1)


    merged_df['elevator'] = merged_df['elevator'].apply(lambda x: 'пассажирский' if x == 'пассажирский и грузовой' else x)

    merged_df = merged_df[merged_df.owner != 'Новостройка'].reset_index(drop=True)
    merged_df.loc[(merged_df.owner=='Неизвестно'), 'owner'] = 'Хозяин недвижимости'

    current_year = datetime.datetime.now().year
    indexes_to_change = merged_df[(merged_df.construction_year>=current_year)&(merged_df.condition.isna())].index
    merged_df.loc[indexes_to_change, 'condition'] = 'черновая отделка'
    indexes_to_change = merged_df[merged_df.condition=='свободная планировка'].index
    merged_df.loc[indexes_to_change, 'condition'] = 'черновая отделка'
    indexes_to_change = merged_df[(merged_df.condition=='требует ремонта')&(merged_df.construction_year>=2020)].index
    merged_df.loc[indexes_to_change, 'condition'] = 'черновая отделка'
    indexes_to_change = merged_df[(merged_df.condition=='требует ремонта')].index
    merged_df.loc[indexes_to_change, 'condition'] = 'среднее'

    replace_dict_complex_class = {
        'эконом': 'economy',
        'комфорт': 'comfort',
        'бизнес': 'business',
        'премиум': 'premium',
    }
    merged_df['complex_class'] = merged_df['complex_class'].replace(replace_dict_complex_class)

    replace_dict_owner = {
        'Риелтор': 'agent',
        'Хозяин недвижимости': 'owner',
    }
    merged_df['owner'] = merged_df['owner'].replace(replace_dict_owner)

    replace_dict_district = {
        'Алматы р-н': 'almaty',
        'Есильский р-н': 'esil',
        'Нура р-н': 'nura',
        'Сарыарка р-н': 'saryarka',
        'Байконур р-н': 'baikonur',
    }
    merged_df['district'] = merged_df['district'].replace(replace_dict_district)

    replace_dict_elevator = {
        'пассажирский': 'yes',
        'нет': 'no',
    } 
    merged_df['elevator'] = merged_df['elevator'].replace(replace_dict_elevator)

    replace_dict_house_type = { 
        'монолитный дом': 'monolithic',
        'кирпичный дом': 'brick',
        'панельный дом': 'panel',
    }
    merged_df['house_type'] = merged_df['house_type'].replace(replace_dict_house_type)

    replace_dict_bathroom_info = { 
        '2': '2 or more',
        'совмещенный': 'combined',
        'раздельный': 'separate',
    }
    merged_df['bathroom_info'] = merged_df['bathroom_info'].replace(replace_dict_bathroom_info)

    replace_dict_parking = { 
        'нет': 'no',
        'подземный': 'underground',
        'надземный': 'aboveground',
    }
    merged_df['parking'] = merged_df['parking'].replace(replace_dict_parking)

    replace_dict_condition = {
        'черновая отделка': 'rough',
        'среднее': 'average',
        'хорошее': 'good',
    }
    merged_df['condition'] = merged_df['condition'].replace(replace_dict_condition)


    return merged_df


def outliers_z_score(data, feature, log_scale=False, left=3, right=3):
    if log_scale:
        x = np.log(data[feature] + 1)
    else:
        x = data[feature]
    mu = x.mean()
    sigma = x.std()
    lower_bound = mu - left * sigma
    upper_bound = mu + right * sigma
    outliers = data[(x < lower_bound) | (x > upper_bound)]
    cleaned = data[(x >= lower_bound) & (x <= upper_bound)]
    return outliers, cleaned


# Function for making a decision on normality
def decision_normality(p, alpha = 0.05  ):
    print('p-value = {:.3f}'.format(p))
    if p <= alpha:
        print('p-value is less than the specified significance level {:.2f}. The distribution differs from normal.'.format(alpha))
    else:
        print('p-value is greater than the specified significance level {:.2f}. The distribution is normal.'.format(alpha))


# Function for making a decision on rejecting the null hypothesis
def decision_hypothesis(p, alpha = 0.05 ):
    print('p-value = {:.3f}'.format(p))
    if p <= alpha:
        print('p-value is less than the specified significance level {:.2f}. We reject the null hypothesis in favor of the alternative.'.format(alpha))
    else:
        print('p-value is greater than the specified significance level {:.2f}. We have no grounds to reject the null hypothesis.'.format(alpha))
