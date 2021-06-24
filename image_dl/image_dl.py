"""This script serves as the main file."""
import os
import re
import time
import pathlib
import asyncio
import aiohttp
from aiohttp import ClientSession
import aiofiles
import logging
from lxml import etree
from urllib.parse import urlparse, urljoin
from utils import parse_args, get_urls, get_download_dir, get_formats

logger = logging.getLogger("image_dl")

import socks
import socket

socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 1086)
socket.socket = socks.socksocket


async def fetch(url, session, formats):
    try:
        async with session.get(url) as response:
            logger.info("Got response [%s] for url: %s", response.status, url)
            res = await response.text()
    except aiohttp.ClientError as e:
        logger.error("aiohttp exception for %s", url, exc_info=e)
    except Exception:
        logger.exception("non-aiohttp exception occurred: %s", url)

    else:
        return res


# TODO: when src is js
async def parse_imgs(url, session, formats):
    image_urls = []
    response = await fetch(url, session, formats)
    lxml_element = etree.HTML(response)
    img_links = lxml_element.xpath(
        "//img/@src | //img/@data-original | //a/@href | //a/@data-original"
    )
    img_list = []
    for link in img_links:
        if urlparse(link).path.split(".")[-1] in formats:
            img_list.append(link)
    for index, img in enumerate(img_list):
        if re.match(r"^//.+", img):
            img_list[index] = "https:" + img
        if re.match(r"^/[^/].+", img):
            img_list[index] = urljoin(url, img)
    return img_list


def process_dir(dl_dir):
    if dl_dir.exists():
        if not os.access(dl_dir, os.W_OK):
            raise DirectoryWriteError
    elif os.access(dl_dir.parent, os.W_OK):
        os.mkdir(dl_dir)
    else:
        raise DirectoryCreateError


# TODO: catch failed imgs
async def save_img(dl_dir, link, session):
    process_dir(dl_dir)
    img_name = link.split("/")[-1]
    if "?" in img_name:
        img_name = img_name.split("?")[0]
    img_path = os.path.join(dl_dir, img_name)
    async with aiofiles.open(img_path, "wb") as f:
        try:
            async with session.get(link) as response:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    await f.write(chunk)
        except aiohttp.client_exceptions.InvalidURL:
            logger.error("aiohttp InvalidURL exception for %s", link)


async def download_imgs(url, session, dir_name, formats):
    img_list = await parse_imgs(url, session, formats)
    dl_dir = get_download_dir(url, dir_name)
    if not img_list:
        return None
    for link in img_list:
        await save_img(dl_dir, link, session)


async def main(urls, dir_name, formats):
    async with ClientSession() as session:
        tasks = []
        for url in urls:
            tasks.append(download_imgs(url, session, dir_name, formats))
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    t1 = time.time()
    args = parse_args()
    urls = get_urls(args)
    dir_name = args.dir
    formats = get_formats(args)
    asyncio.run(main(urls, dir_name, formats))
    print("Time Taken: ", time.time() - t1)
