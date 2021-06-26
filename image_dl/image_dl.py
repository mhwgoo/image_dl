"""This script serves as the main file."""
import os
import sys
import re
import random
import time
import pathlib
import requests
import concurrent.futures
from threading import Lock
from lxml import etree
from urllib.parse import urlparse, urljoin
from fake_user_agent.main import user_agent


from utils import parse_args, get_url, get_download_dir
from log import logger
from exceptions import DirectoryAccessError, DirectoryCreateError

# import socks
# import socket
# socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 1086)
# socket.socket = socks.socksocket

ua = user_agent()
headers = {"User-Agent": ua}


def fetch(url, session):
    try:
        with session.get(url, headers=headers) as r:
            logger.info(
                "Got response [%s] for url: %s : returned url: %s",
                r.status_code,
                url,
                r.url,
            )
            res = r.text
    except requests.exceptions.MissingSchema:
        logger.error("Invalid URL: %s", link)
        raise
    except requests.exceptions.ConnectionError:
        logger.error("Error occurred when fetching %s", url)
        raise
    except Exception:
        logger.error("Error occurred when fetching  %s", url)
        raise
    else:
        return res


def fetch_js(url):
    from selenium import webdriver

    try:
        driver = webdriver.Chrome()
        driver.get(url)
        html = driver.page_source
        driver.quit()
    except Exception:
        logger.error("You are blocked by the web server of %s.", url, exc_info=True)
    else:
        return html


def parse(response, formats):
    img_list = []
    lxml_element = etree.HTML(response)
    img_links = lxml_element.xpath("//img/@src")
    if img_links:
        img_list.extend(img_links)
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
    img_list = parse(response, formats)
    if not img_list:
        logger.info("No images found by 'fetch' in the webpage.")
        r = fetch_js(url)
        imgs = parse(r, formats)
        if not imgs:
            logger.info("No images found by 'fetch_js' in the webpage.")
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


def save_img(dl_dir, link, session, formats):
    process_dir(dl_dir)
    img_name = "_".join(link.split("/")[-2:])
    # with Lock():
    #    random_id = str(random.gauss(1, 1))
    # img_name = random_id + "_" + link.split("/")[-1]
    if "?" in img_name:
        img_name = img_name.split("?")[0]
    if img_name.split(".")[-1] not in formats:
        img_name = img_name + ".jpg"
    img_path = os.path.join(dl_dir, img_name)

    with open(img_path, "wb") as f:
        try:
            with session.get(link, headers=headers, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
        except Exception:
            logger.error("Error occurred when fetching  %s", link, exc_info=True)
            pass


def download_imgs(url, dl_dir, formats):
    with requests.Session() as session:
        img_list = parse_imgs(url, session, formats)
        print("There are  %s image links", len(img_list))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for link in img_list:
                logger.info("%s is starting to download", link)
                executor.submit(save_img, dl_dir, link, session, formats)
                logger.info("%s done downloading", link)


if __name__ == "__main__":
    t1 = time.time()
    args = parse_args()
    url = get_url(args)
    dl_dir = get_download_dir(url, args.dir)
    formats = args.formats
    download_imgs(url, dl_dir, formats)
    print("Time Taken: ", time.time() - t1)
