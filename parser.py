#!/usr/bin/python2.7
"""Simple scraper for NASDAQ data."""
import os
import csv
import logging
from sys import argv
from datetime import datetime

import requests
from bs4 import BeautifulSoup


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
try:
    str(argv[1])
except IndexError:
    logging.critical('Please pass dump folder name as first parameter!')
    exit(1)
timestamp = datetime.now()
path = argv[1] + '/' + datetime.strftime(timestamp, '/%Y/%m/%d/%H%M%S/')
# Starting session for extra speed and connection liability
requests = requests.Session()
URL = 'https://community.nasdaq.com/most-rated-stocks.aspx'
basic_parameter = 'ctl00$ContentPlaceHolder$btn{}Ratings'
page_parameter = 'ctl00$ContentPlaceHolder$MostRated{}Stocks'
next_page = 'ctl00_ContentPlaceHolder_MostRated{}Stocks_lb_NextPage'


def get_website_data():
    """Scraper of pages from target source."""
    headers = {'User-Agent':
               """Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) """
               """Gecko/20100101 Firefox/53.0""",
               'Referer':
               'https://community.nasdaq.com/most-rated-stocks.aspx'}
    payload = {'__EVENTTARGET':
               '',
               '__VIEWSTATEENCRYPTED':
               ''}
    # Fake activity to get form params for whole session and a Bulls page
    r = requests.get(URL,
                     headers=headers)
    r_soup = BeautifulSoup(r.text, 'html.parser')
    payload['__EVENTVALIDATION'] =\
        r_soup.find('input', {'id': '__EVENTVALIDATION'})['value']
    payload['__VIEWSTATE'] =\
        r_soup.find('input', {'id': '__VIEWSTATE'})['value']
    payload['__VIEWSTATEGENERATOR'] =\
        r_soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            logging.critical("""Error while creating reports folder! """
                             """Please check permissions or folder name.""")
    with open(path + 'data.csv', 'w') as csvfile:
        fieldnames = ['Symbol', 'Company',
                      'Direction', 'Consensus',
                      'TimeStamp']
        writer = csv.DictWriter(csvfile,
                                fieldnames=fieldnames)
        writer.writeheader()
        for name in ["Bull", "Bear"]:
            logging.info('Parsing {} pages...'.format(name))
            payload['__EVENTTARGET'] =\
                basic_parameter.format(name + 'ish')
            p = requests.post(URL,
                              data=payload, headers=headers)
            p_soup = BeautifulSoup(p.text, 'html.parser')
            logging.info('Page 1... OK')
            for rate in get_page_data(p_soup, name):
                writer.writerow(rate)
            starting_page = 2
            while True:
                payload['__EVENTTARGET'] =\
                    page_parameter.format(name) +\
                    '$lb_{}'.format(starting_page)
                p = requests.post(URL,
                                  data=payload, headers=headers)
                p_soup = BeautifulSoup(p.text, 'html.parser')
                # Breaking on 1-page case or if no pages left
                try:
                    if int(p_soup.find('a',
                                       {'id':
                                        next_page.format(name)
                                        }).find_previous_sibling('a').text) <\
                            starting_page:
                        break
                except AttributeError:
                    break
                for rate in get_page_data(p_soup, name):
                    writer.writerow(rate)
                logging.info('Page {}... OK'.format(starting_page))
                starting_page += 1


def get_page_data(soup, direction):
    """Parser of actual rating tables into dictionaries."""
    ratings = []
    try:
        for i in soup.find('table',
                           {'class':
                            'mostRatedStocks'}).findAll('tr')[1:]:
            page_dict = {}
            page_dict['Symbol'] = i.a.text.strip()
            page_dict['Company'] = i.findAll('td')[1].text
            page_dict['Direction'] = direction
            page_dict['Consensus'] = i.span.text
            page_dict['TimeStamp'] = datetime.strftime(timestamp,
                                                       '%Y-%m-%d %H:%M:%S')
            ratings.append(page_dict)
    except (AttributeError, IndexError):
        return
    return ratings


if __name__ == '__main__':
    get_website_data()
