"""This script serves as the main file."""
import os
import sys
import re
import time
import requests
import http.client
import concurrent.futures
from threading import Lock
from lxml import etree
from urllib.parse import urlparse, urljoin
from fake_user_agent.main import user_agent

from .arg import parse_args, get_url, get_download_dir
from .progressbar import update
from .log import logger
from .exceptions import DirectoryCreateError


ua = user_agent()
headers = {"User-Agent": ua}
count = 0
OP = ["FETCHING", "PARSING"]

def fetch(url, session):
    session.headers.update(headers)
    attempt = 0 

    while True:
        try:
            r = session.get(url, timeout=9.05)
        except requests.exceptions.HTTPError as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        except requests.exceptions.ConnectTimeout as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        except requests.exceptions.ConnectionError as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        except requests.exceptions.ReadTimeout as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        else:
            return r.text


def call_on_error(error, url, attempt, op):
    attempt += 1
    logger.debug(
        "%s HTML from %s %d times",
        op,
        url,
        attempt,
    )
    if attempt == 3:
        logger.debug("Maximum %s retries reached. Exit", op)
        logger.error(str(error))
        sys.exit()
    return attempt


def fetch_js(url):
    from selenium import webdriver

    try:
        driver = webdriver.Chrome()
        driver.get(url)
        html = driver.page_source
        driver.quit()
    except http.client.RemoteDisconnected as e:
        logger.error(
            "Scraper is blocked by the web server of %s with error: %s", url, str(e) 
        )
        sys.exit()
    except Exception as e:
        logger.error("%s when fetching %s", str(e), url, exc_info=True)
    else:
        return html


def parse(url, response, formats):
    img_list = []
    lxml_element = etree.HTML(response)
    img_links = lxml_element.xpath("//img/@src")
    if img_links:
        for link in img_links:
            if urlparse(link).path.split(".")[-1] in formats:
                img_list.append(link)
    a_links = lxml_element.xpath("//a/@href | //a/@data-original")
    if a_links:
        for link in a_links:
            if urlparse(link).path.split(".")[-1] in formats:
                img_list.append(link)
    if img_list:
        for index, img in enumerate(img_list):
            img = img.strip()
            if re.match(r"^//.+", img):
                img_list[index] = "https:" + img
            if re.match(r"^/[^/].+", img):
                img_list[index] = urljoin(url, img)
        img_list = list(filter(None, img_list))
        return img_list


def parse_imgs(url, session, formats):
    response = fetch(url, session)
    img_list = parse(url, response, formats)
    if not img_list:
        logger.info("No images found in the webpage.")
        r = fetch_js(url)
        imgs = parse(r, formats)
        if not imgs:
            logger.info("No images found also by reading js in the webpage.")
            sys.exit()
        else:
            return imgs
    else:
        return img_list


def process_dir(dl_dir):
    if dl_dir.exists():
        if not os.access(dl_dir, os.W_OK):
            raise DirectoryWriteError
    elif os.access(dl_dir.parent, os.W_OK):
        os.mkdir(dl_dir)
    else:
        raise DirectoryCreateError


def save_img(f, link, session):
    try:
        with session.get(link, headers=headers, stream=True) as r:
            for chunk in r.iter_content():
                f.write(chunk)
    except Exception as e:
        logger.error("%s when fetching  %s", str(e), link, exc_info=True)


def download():
    args = parse_args()
    url = get_url(args.url)
    dl_dir = get_download_dir(url, args.dir)
    formats = args.formats
    with requests.Session() as session:
        print("Requesting page...\n")
        t1 = time.time()
        img_list = parse_imgs(url, session, formats)
        img_num = len(img_list)
        print(f"Found {img_num} images:")
        lock = Lock()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for i, link in enumerate(img_list):
                process_dir(dl_dir)
                img_name = "_".join(link.split("/")[-2:])
                if "?" in img_name:
                    img_name = img_name.split("?")[0]
                if img_name.split(".")[-1] not in formats:
                    img_name = img_name + ".jpg"
                img_path = os.path.join(dl_dir, img_name)

                f = open(img_path, "wb")
                update(i, img_num)
                executor.submit(save_img, f, link, session)
                global count
                lock.acquire()
                count += 1
                lock.release()
                f.close()

            update(img_num, img_num)

        t2 = time.time()
        print("Done!")
        print(f"Downloaded {count} images")
        print(f"Failed: {img_num - count}")
        print(f"Time Taken: {t2-t1}")


def main():
    try:
        download()
    except KeyboardInterrupt:
        print("\nOpt out by user.")
