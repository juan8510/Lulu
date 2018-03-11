#!/usr/bin/env python

import re
from urllib import parse
from html import unescape

from lulu.common import (
    match1,
    get_head,
    url_info,
    print_info,
    get_content,
    download_urls,
    download_url_ffmpeg,
    playlist_not_supported,
)
from lulu.config import FAKE_HEADERS
from lulu.extractors.embed import embed_download


__all__ = ['universal_download']


def universal_download(
    url, output_dir='.', merge=True, info_only=False, **kwargs
):
    try:
        content_type = get_head(url, headers=FAKE_HEADERS)['Content-Type']
    except Exception:
        content_type = get_head(
            url, headers=FAKE_HEADERS, get_method='GET'
        )['Content-Type']
    if content_type.startswith('text/html'):
        try:
            embed_download(
                url, output_dir=output_dir, merge=merge, info_only=info_only,
                **kwargs
            )
        except Exception:
            pass
        else:
            return

    domains = url.split('/')[2].split('.')
    if len(domains) > 2:
        domains = domains[1:]
    site_info = '.'.join(domains)

    if content_type.startswith('text/html'):
        # extract an HTML page
        response = get_content(url)
        page = str(response)

        page_title = match1(page, r'<title>([^<]*)')
        if page_title:
            page_title = unescape(page_title)

        hls_urls = re.findall(
            r'(https?://[^;"\'\\]+' + '\.m3u8?' + r'[^;"\'\\]*)', page
        )
        if hls_urls:
            for hls_url in hls_urls:
                type_, ext, size = url_info(hls_url)
                print_info(site_info, page_title, type_, size)
                if not info_only:
                    download_url_ffmpeg(
                        url=hls_url, title=page_title, ext='mp4',
                        output_dir=output_dir
                    )
            return

        # most common media file extensions on the Internet
        media_exts = [
            '\.flv', '\.mp3', '\.mp4', '\.webm',
            '[-_]1\d\d\d\.jpe?g', '[-_][6-9]\d\d\.jpe?g',  # tumblr
            '[-_]1\d\d\dx[6-9]\d\d\.jpe?g',
            '[-_][6-9]\d\dx1\d\d\d\.jpe?g',
            '[-_][6-9]\d\dx[6-9]\d\d\.jpe?g',
            's1600/[\w%]+\.jpe?g',  # blogger
            'img[6-9]\d\d/[\w%]+\.jpe?g',  # oricon?
        ]

        urls = []
        for i in media_exts:
            urls += re.findall(
                r'(https?://[^;"\'\\]+' + i + r'[^;"\'\\]*)', page
            )

            p_urls = re.findall(
                r'(https?%3A%2F%2F[^;&]+' + i + r'[^;&]*)', page
            )
            urls += [parse.unquote(url) for url in p_urls]

            q_urls = re.findall(
                r'(https?:\\\\/\\\\/[^;"\']+' + i + r'[^;"\']*)', page
            )
            urls += [url.replace('\\\\/', '/') for url in q_urls]

        # a link href to an image is often an interesting one
        urls += re.findall(r'href="(https?://[^"]+\.jpe?g)"', page, re.I)
        urls += re.findall(r'href="(https?://[^"]+\.png)"', page, re.I)
        urls += re.findall(r'href="(https?://[^"]+\.gif)"', page, re.I)

        # MPEG-DASH MPD
        mpd_urls = re.findall(r'src="(https?://[^"]+\.mpd)"', page)
        for mpd_url in mpd_urls:
            cont = get_content(mpd_url)
            base_url = match1(cont, r'<BaseURL>(.*)</BaseURL>')
            urls += [match1(mpd_url, r'(.*/)[^/]*') + base_url]

        # have some candy!
        candies = []
        i = 1
        for url in set(urls):
            filename = parse.unquote(url.split('/')[-1])
            if 5 <= len(filename) <= 80:
                title = '.'.join(filename.split('.')[:-1])
            else:
                title = '{}'.format(i)
                i += 1

            candies.append({
                'url': url, 'title': title
            })

        for candy in candies:
            try:
                mime, ext, size = url_info(candy['url'])
                if not size:
                    size = float('Int')
            except Exception:
                continue
            else:
                print_info(site_info, candy['title'], ext, size)
                if not info_only:
                    download_urls(
                        [candy['url']], candy['title'], ext, size,
                        output_dir=output_dir, merge=merge
                    )
        return

    else:
        # direct download
        filename = parse.unquote(url.split('/')[-1])
        title = '.'.join(filename.split('.')[:-1])
        ext = filename.split('.')[-1]
        _, _, size = url_info(url)
        print_info(site_info, title, ext, size)
        if not info_only:
            download_urls(
                [url], title, ext, size, output_dir=output_dir, merge=merge
            )
        return


site_info = None
download = universal_download
download_playlist = playlist_not_supported('universal')
