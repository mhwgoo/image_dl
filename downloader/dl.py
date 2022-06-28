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
total = 0 
ops = ["FETCHING", "FETCHING_JS", "PARSING", "SAVING"]
base_page_text ="" 
base_page_url = ""

# Support downloading all at once & by chunk
def fetch(url, session, stream=False):
    session.headers.update(headers)
    attempt = 0 

    while True:
        try:
            r = session.get(url, timeout=9.05, stream=stream)
        except requests.exceptions.HTTPError as e:
            attempt = call_on_error(e, url, attempt, ops[0])
        except requests.exceptions.ConnectTimeout as e:
            attempt = call_on_error(e, url, attempt, ops[0])
        except requests.exceptions.ConnectionError as e:
            attempt = call_on_error(e, url, attempt, ops[0])
        except requests.exceptions.ReadTimeout as e:
            attempt = call_on_error(e, url, attempt, ops[0])
        except Exception as e:
            attempt = call_on_error(e, url, attempt, ops[0])
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
        attempt = call_on_error(e, url, attempt, ops[1])
    except Exception as e:
        attempt = call_on_error(e, url, attempt, ops[1])
    else:
        return page_source 


def parse_links():
    lxml_element = etree.HTML(base_page_text)
    link_nodes = lxml_element.xpath("//ul/li/a")
    links = []
    for l in link_nodes:
        loc = l.attrib["href"] 
        name = l.text
        if not loc.startswith("http"):
            loc = base_page_url + loc
        pair = (name, loc)
        links.append(pair) 
    return links


def parse_imgs(formats):
    img_list = []
    lxml_element = etree.HTML(base_page_text)
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
                img_list[index] = urljoin(base_page_url, img)
        img_list = set(filter(None, img_list))  # When None is used as the first argument to the filter function, all elements that are truthy values (gives True if converted to boolean) are extracted.
        return img_list


def parse(formats):
    img_list = parse_imgs(formats)
    if not img_list:
        logger.info("No images found in the webpage. Refetching...")
        r = fetch_js(base_page_url)
        global base_page_text
        base_page_text = r
        imgs = parse_imgs(formats)
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


def save_img(session, link, dir, formats):
    r = fetch(link, session, stream=True)
    path = process_img_path(dir, formats, link)

    try: 
        with open(path, "wb") as f:  # for stream=True, you have to use with open, otherwise it will generate "write to closed file" error
            for chunk in r:
                f.write(chunk)
        logger.debug("Saved file to %s", path)
    except Exception as e:
        logger.debug(str(e))


def save_to_markdown(session, link, dir=None, level=1, title=None):
    # Get nodes 
    text = base_page_text
    if level == 2:
        r = fetch(link, session)
        text = r.text
    lxml_element = etree.HTML(text)
    
    # Extract title
    if title is None:
        # FIXME not always right 
        title = text.split("<title>")[1].split("</title>")[0]
    title = title.split("?")[0]

    # Create file path
    path = title + ".md"
    if dir is not None:
        process_dir(dir)
        path = os.path.join(dir, path)

    # Narrow down to article nodes if any
    article = re.search(r'<article.*/article>', text, re.S)
    if article:
        # replaced = re.sub(r'<\/?strong>|<\/?b>', "", article.group())
        lxml_element = etree.HTML(article.group())
    # replaced = re.sub(r'<\/?strong>|<\/?b>', "", text)

    # Write to file
    try:
        with open(path, "w") as f:
            # Xpath will sort the returned list according the order in the source
            sentences = lxml_element.xpath("//p | //h1 | //h2 | //h3 | //blockquote | //img | //hr")
            for s in sentences:
                tag = s.tag

                # FIXME How to get descendents, siblings, etc, i.e. how to inspect a node
                if tag == "p": 
                    if s.text is not None:
                        f.write(s.text)
                    children = s.getchildren() 
                    if children:
                        for i in children:
                            if i.tag == "br":
                                f.write(i.tail + "\n")
                            if i.tag == "font" or i.tag == "strong" or i.tag == "b" or i.tag == "em":
                                f.write(i.text)
                            if i.tag == "img":
                                continue
                    f.write("\n")

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
                            loc = s.attrib["src"]
                        except Exception as e:
                            continue
                        else:
                            if loc.startswith("http"):
                                f.write("\n![image]" + "(" + loc + ")" + "\n\n")
                            else:
                                f.write("\n![image]" + "("  + s.attrib["data-original"] + ")" + "\n\n")
                if tag == "hr":
                    f.write("\n---\n")

            f.write("\n---\n原文: " + link)
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
    global base_page_text
    global base_page_url

    with requests.Session() as session:

        print(f"{ops[0]} {url} ...")
        response = fetch(url, session)
        base_page_text = response.text
        base_page_url = response.url

        if args.subparser_name == "image":
            formats = args.format

            print(f"{ops[2]} {url} ...")
            img_list = parse(formats)
            total = len(img_list)
            print(f"FOUND {total} files")
            print(f"{ops[3]} files ...")
            update(count, total)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for link in img_list:
                    executor.submit(save_img, session, link, dir, formats)
                    lock.acquire()
                    count += 1
                    lock.release()
                    update(count, total)

        if args.subparser_name == "html":
            level = int(args.level)

            if level == 1:
                print(f"{ops[2]} {url} ...")
                total += 1 
                print(f"FOUND {total} files")
                print(f"{ops[3]} files ...")
                update(count, total)
                save_to_markdown(session, base_page_url)
                count += 1
                update(count, total)

            if level == 2:
                print(f"{ops[2]} {url} ...")
                link_list = parse_links()
                total = len(link_list)
                print(f"FOUND {total} files")
                print(f"{ops[3]} files ...")
                update(count, total)
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    for i in link_list:
                        title = i[0]
                        link = i[1]
                        executor.submit(save_to_markdown, session, link, dir, level, title)
                        lock.acquire()
                        count += 1
                        lock.release()
                        update(count, total)

    print("DONE!")
    print(f"DOWNLOADED {count} files")
    print(f"FAILED: {total - count}")


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
