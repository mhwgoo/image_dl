"""This script serves as the main file."""
import os
import sys
import re
import time
import base64
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
total = 0 

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
            if r.status_code == 200:  # only a 200 response has a response body
                logger.debug("%s has fetched successfully", url)
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


def parse_links(url, response):
    html_content = response.text
    lxml_element = etree.HTML(html_content)
    link_nodes = lxml_element.xpath("//ul/li/a")
    links = []
    for l in link_nodes:
        loc = l.attrib["href"] 
        if not loc.startswith("http"):
            loc = url + loc
        links.append(loc) 
    return links


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
        img_list = set(filter(None, img_list))  # When None is used as the first argument to the filter function, all elements that are truthy values (gives True if converted to boolean) are extracted.
        return img_list


def parse(url, response, formats):
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
    # Ask forgiveness, not permission
    try:
        os.mkdir(dir)
    except FileExistsError:
        return
    except OSError as e:
        logger.error(str(e))
        sys.exit()


def process_img_path(dir, formats, link):
    process_dir(dir)

    img_name = "_".join(link.split("/")[-2:])
    if "?" in img_name:
        img_name = img_name.split("?")[0]
    if img_name.split(".")[-1] not in formats:
        img_name = img_name + ".jpg"
    img_path = os.path.join(dir, img_name)
    return img_path


def save_img(dir, formats, link, session):
    r = fetch(link, session, stream=True)
    path = process_img_path(dir, formats, link)

    try: 
        with open(path, "wb") as f:  # for stream=True, you have to use with open, otherwise it will generate "write to closed file" error
            for chunk in r:
                f.write(chunk)
        logger.debug("Saved file to %s", path)
    except Exception as e:
        logger.debug(str(e))


# FIXME: br in p, li in ul
def save_to_markdown(response):
    html_content = response.text
    url = response.url
    
    # Extract title
    lxml_element = etree.HTML(html_content)
    title = lxml_element.xpath("/html/head/title/text()")[0].replace(" ", "")
    characters = ["?", ":", "-", "_", "."]
    for c in characters:
        title = title.split(c)[0]

    # Extract article body
    article = re.search(r'<article.*/article>', html_content, re.S)
    if article:
        replaced = re.sub(r'<\/?strong>|<\/?b>|<br>', "", article.group())
    else:
        replaced = re.sub(r'<\/?strong>|<\/?b>|<br>', "", html_content)
    lxml_replaced = etree.HTML(replaced)
    path = title + ".md"

    try:
        with open(path, "w") as f:
            # Xpath will sort the returned list according the order in the source

            # sentences = lxml_replaced.xpath("//p | //h1 | //h2 | //h3 | //blockquote | //img")
            sentences = lxml_replaced.xpath("//p | //h1 | //h2 | //h3 | //blockquote | //img")
            for s in sentences:
                tag = s.tag
                if tag == "p": 
                    if s.text is not None:
                        f.write(s.text + "\n")
                if tag == "h1": 
                    f.write("# " + s.text + "\n")
                if tag == "h2":
                    f.write("\n## " + s.text + "\n")
                if tag== "h3":
                    f.write("\n### " + s.text + "\n")

                # Handle all text of a blockquote node, including that of its br child node
                if tag == "blockquote":
                    f.write("\n")
                    f.write("> " + s.text + "\n")
                    for i in s.getchildren():
                        f.write("> " + i.tail + "\n")
                    f.write("\n")

                if tag == "img":
                    parent = s.getparent()
                    if parent.tag != "noscript":
                        try: 
                            link = s.attrib["src"]
                        except Exception as e:
                            continue
                        else:
                            if link.startswith("http"):
                                f.write("\n![image]" + "(" + link + ")" + "\n\n")
                            else:
                                f.write("\n![image]" + "("  + s.attrib["data-original"] + ")" + "\n\n")

            f.write("\n---\n原文: " + url)
        logger.debug("Saved file to %s", path)
    except Exception as e:
        logger.debug(str(e))


def download():
    args = parse_args()
    url = get_url(args.url)
    dir = get_download_dir(url, args.dir)
    lock = Lock()
    global total
    global count

    with requests.Session() as session:

        print(f"Fetching {url} ...")
        response = fetch(url, session)

        if args.subparser_name == "image":
            formats = args.format

            print(f"Parsing {url} ...")
            img_list = parse(url, response, formats)
            total = len(img_list)
            print(f"Found {total} files")
            print("Saving files ...")
            update(count, total)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for link in img_list:
                    executor.submit(save_img, dir, formats, link, session)
                    lock.acquire()
                    count += 1
                    lock.release()
                    update(count, total)

        if args.subparser_name == "html":
            if args.level == 1:
                print(f"Parsing {url} ...")
                total += 1 
                print(f"Found {total} files")
                print("Saving files ...")
                update(count, total)
                save_to_markdown(response)
                count += 1
                update(count, total)

            if args.level == 2:
                link_list = parse_links(url, response)
                total = len(link_list)
                print(f"Found {total} files")

                # FIXME: multi-thread fetch and save
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    for link in link_list:
                        response = fetch(link, session)
                        executor.submit(save_to_markdown, response)
                        lock.acquire()
                        count += 1
                        lock.release()
                        update(count, total)

    print("Done!")
    print(f"Downloaded {count} files")
    print(f"Failed: {total - count}")


def main():
    try:
        t1 = time.time()
        download()
        t2 = time.time()
        print(f"\nTime Taken: {t2-t1}")

    except KeyboardInterrupt:
        print("\nCancelled out by user.")


if __name__ == "__main__":
    from args import parse_args, get_url, get_download_dir
    from progressbar import update
    from log import logger

else:
    from .args import parse_args, get_url, get_download_dir
    from .progressbar import update
    from .log import logger

main()
