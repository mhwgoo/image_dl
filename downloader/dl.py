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


ua = user_agent()
headers = {"User-Agent": ua}
count = 0
OP = ["FETCHING", "FETCHING_JS", "PARSING"]


# Support downloading all at once & by chunk
def fetch(url, session, stream=False):
    session.headers.update(headers)
    attempt = 0 

    while True:
        try:
            r = session.get(url, timeout=9.05, stream=stream)
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
            if r.ok:
                return r


def call_on_error(error, url, attempt, op):
    attempt += 1
    logger.debug(
        "%s file from %s %d times",
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

    attempt = 0 
    try:
        driver = webdriver.Chrome()
        driver.get(url)
        page_source = driver.page_source
        driver.quit()
    except http.client.RemoteDisconnected as e:
        attempt = call_on_error(e, url, attempt, OP[1])
    except Exception as e:
        attempt = call_on_error(e, url, attempt, OP[1])
    else:
        return page_source 


def parse_imgs(url, response, formats):
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


def parse(url, session, formats):
    response = fetch(url, session)

    img_list = parse_imgs(url, response.text, formats)
    if not img_list:
        logger.info("No images found in the webpage. Refetching...")
        r = fetch_js(url)
        imgs = parse_imgs(url, r, formats)
        if not imgs:
            logger.info("No images found also by reading js in the webpage.")
            sys.exit()
        else:
            return imgs
    else:
        return img_list


def process_dir(dir):
    if dir.exists():
        if not os.access(dir, os.W_OK):
            logger.error("The directory %s can not be accessed.", dir)
            sys.exit()
    elif os.access(dir.parent, os.W_OK):
        os.mkdir(dir)
    else:
        logger.error("The directory %s can not be created.", dir)
        sys.exit()


def save(f, link, session):
    # with session.get(link, headers=headers, stream=True) as r:
    r = fetch(link, session, stream=True)
    for chunk in r.iter_content():
        f.write(chunk)

def download():
    args = parse_args()
    url = get_url(args.url)
    dir = get_download_dir(url, args.dir)

    with requests.Session() as session:
        if args.subparser_name == "image" and args.format:
            formats = args.format
            t1 = time.time()

            print("Requesting page...\n")
            img_list = parse(url, session, formats)
            img_num = len(img_list)
            print(f"Found {img_num} images:")

            lock = Lock()

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for i, link in enumerate(img_list):
                    process_dir(dir)
                    img_name = "_".join(link.split("/")[-2:])
                    if "?" in img_name:
                        img_name = img_name.split("?")[0]
                    if img_name.split(".")[-1] not in formats:
                        img_name = img_name + ".jpg"
                    img_path = os.path.join(dir, img_name)

                    f = open(img_path, "wb")
                    executor.submit(save, f, link, session)
                    global count
                    lock.acquire()
                    count += 1
                    update(count, img_num)
                    lock.release()
                    f.close()

            print("Done!")
            print(f"Downloaded {count} images")
            print(f"Failed: {img_num - count}")

            t2 = time.time()
            print(f"\nTime Taken: {t2-t1}")

    if args.subparser_name == "html":
        pass


def main():
    try:
        download()
    except KeyboardInterrupt:
        print("\nOpt out by user.")


if __name__ == "__main__":
    from args import parse_args, get_url, get_download_dir
    from progressbar import update
    from log import logger
    main()

else:
    from .args import parse_args, get_url, get_download_dir
    from .progressbar import update
    from .log import logger

