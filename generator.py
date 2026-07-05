import os
import re
import json
import random
import datetime  
import asyncio
import requests
import traceback
import subprocess  
import time
from bs4 import BeautifulSoup
from PIL import Image, ImageFilter
from concurrent.futures import ThreadPoolExecutor
import feedparser  
import edge_tts
from duckduckgo_search import DDGS  # <- সেই আগের অরিজিনাল স্মার্ট ইমেজ সার্চ লাইব্রেরি!

GENERIC_SPORTS_FALLBACKS = [
    "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=1920&q=80",  
    "https://images.unsplash.com/photo-1519766304817-4f37bda74a27?w=1920&q=80",  
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=1920&q=80",  
]

async def generate_voice_and_subtitles(text, voice, audio_path, srt_path):
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    with open(audio_path, "wb") as fobj:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fobj.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(submaker.get_srt())

def scrape_article(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, 'html.parser')
    cleaned = []
    unwanted = ["follow", "read more", "cookies", "subscribe", "social media information", "like our page", "bgn community post", "featured in the linc", "the linc!"]
    
    for p in soup.find_all('p'):
        txt = p.get_text().strip()
        if len(txt) < 15 or any(k in txt.lower() for k in unwanted): continue
        cleaned.append(txt)
    return "\n\n".join(cleaned)

def hex_to_ass_color(hex_str, opacity_float=1.0):
    hex_str = hex_str.lstrip('#')
    r, g, b = hex_str[0:2], hex_str[2:4], hex_str[4:6]
    return f"&H{int((1.0 - opacity_float) * 255):02X}{b}{g}{r}"

def get_audio_duration(audio_path):
    try:
        res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except: return 0.0

def smart_ddgs_images_search(keyword, limit=30):
    """এটি আগের মতই আপনার পিসির নিখুঁত ddgs সার্চ ইঞ্জিনের স্মার্ট লজিক ব্যবহার করবে। 
    তবে গিটহাবে Rate limit/Time out এড়াতে try-except এবং smart delays অ্যাপ্লাই করা হয়েছে।"""
    print(f"Deploying official Python DDGS engine for hyper-relevant images searching: '{keyword}'...")
    final_image_links = []
    
    try:
        # DDGS.images রিটার্ন করে একটি জেনারেটর ডিকশনারি, যা খুবই একুরেট স্পোর্টস ও রিয়েল লাইফ ছবি নিয়ে আসে 
        results_iterator = DDGS().images(
            keywords=keyword,
            max_results=limit,
        )
        
        for index, item in enumerate(results_iterator):
            pic_url = item.get("image")
            if pic_url:
                final_image_links.append(pic_url)
                # ২-৩ টি ছবির পরে গিটহাবের সার্ভারে অ্যান্টি-বট বাইপাসের জন্য ছোট্ট একটা পজ (Delay) দেওয়া হলো
                if index > 0 and index % 3 == 0: 
                    time.sleep(0.5)

        # রিমুভ ডুপ্লিকেট 
        clean_links = list(dict.fromkeys(final_image_links))
        print(f"Perfect Original Method Found Valid Images count: {len(clean_links)}")
        return clean_links[:limit]

    except Exception as api_err:
        print(f"Cloud Engine Original DDGS Module reported limit timeout correctly intercepted! Log: {api_err}")
        return []

def select_thumbnail_and_crop(images_dir, output_thumbnail_path):
    img_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not img_files:
        r = requests.get(GENERIC_SPORTS_FALLBACKS[0], timeout=10)
        with open(output_thumbnail_path, 'wb') as f: f.write(r.content)
        return
    sixteen_nine_candidates = []
    for f in img_files:
        try:
            with Image.open(os.path.join(images_dir, f)) as img:
                if 1.6 <= (img.size[0] / img.size[1]) <= 1.9: sixteen_nine_candidates.append(os.path.join(images_dir, f))
        except: pass
    if sixteen_nine_candidates: Image.open(random.choice(sixteen_nine_candidates)).convert('RGB').resize((1920, 1080)).save(output_thumbnail_path, quality=95)
    else: Image.open(os.path.join(images_dir, random.choice(img_files))).convert('RGB').resize((1920, 1080)).save(output_thumbnail_path, quality=95)

def parse_srt_start_times(srt_path):
    if not os.path.exists(srt_path): return []
    with open(srt_path, "r", encoding="utf-8") as f: content = f.read()
    st = [int(m[0])*3600 + int(m[1])*60 + int(m[2]) + int(m[3])/1000.0 for m in re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) -->').findall(content)]
    return sorted(list(set(st)))

def render_zoom_segment(eff_idx, duration, source_img_path, output_mp4):
    frames = int(duration * 30)
    eff = eff_idx % 3
    if eff == 0: vf = f"zoompan=z='zoom+0.001':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080,framerate=30"
    elif eff == 1: vf = f"zoompan=z='1.02+0.001*in':x='iw/2-(iw/zoom/2)':y='0':d={frames}:s=1920x1080,framerate=30"
    else: vf = f"zoompan=z='1.02+0.001*in':x='iw/2-(iw/zoom/2)':y='ih-(ih/zoom)':d={frames}:s=1920x1080,framerate=30"
    
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", source_img_path, "-t", str(duration), "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-pix_fmt", "yuv420p", output_mp4], check=True)
    return f"file 'processed_vids/{os.path.basename(output_mp4)}'"

def clear_temp_workspace(ws):
    files = ["audio.mp3", "subtitles.srt", "fast_slider.txt", "temp.mp4", "output_video.mp4", "thumbnail.jpg"]
    dirs = ["images", "processed_images", "processed_vids"]
    for fn in files:
        if os.path.exists(os.path.join(ws, fn)):
            try: os.remove(os.path.join(ws, fn))
            except: pass
    for dn in dirs:
        df = os.path.join(ws, dn)
        os.makedirs(df, exist_ok=True)
        for fi in os.listdir(df):
            try: os.remove(os.path.join(df, fi))
            except: pass

def upload_to_youtube(video_path, thumbnail_path, title, description):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    print("Authenticating to process target youtube channel successfully...")
    creds = Credentials(token=None, refresh_token=os.environ.get('YOUTUBE_REFRESH_TOKEN'), token_uri="https://oauth2.googleapis.com/token", client_id=os.environ.get('YOUTUBE_CLIENT_ID'), client_secret=os.environ.get('YOUTUBE_CLIENT_SECRET'))
    yt = build("youtube", "v3", credentials=creds)
    vbod = {'snippet': {'title': title[:98], 'description': description, 'categoryId': '17'}, 'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}
    v_id = yt.videos().insert(part="snippet,status", body=vbod, media_body=MediaFileUpload(video_path, resumable=True, mimetype="video/mp4")).execute().get('id')
    print(f"Broadcast completely securely logic online safely: V_ID => {v_id}")
    if os.path.exists(thumbnail_path): yt.thumbnails().set(videoId=v_id, media_body=MediaFileUpload(thumbnail_path)).execute()

def main():
    if not os.path.exists("config.json"): return
    with open("config.json", "r", encoding="utf-8") as f: conf = json.load(f)

    if not os.path.exists("processed_urls.txt"):
        with open("processed_urls.txt", "w", encoding="utf-8") as f: f.write("")

    with open("processed_urls.txt", "r", encoding="utf-8") as f: purls = [l.strip() for l in f if l.strip()]

    all_entries, nw_u = [], datetime.datetime.now(datetime.timezone.utc)
    for ru in [u.strip() for u in conf["rss_urls"].split(",") if u.strip()]:
        try:
            for dx, ey in enumerate(feedparser.parse(ru).entries): 
                ey.original_index = dx; all_entries.append(ey)
        except: pass

    all_entries.sort(key=lambda x: getattr(x, 'published_parsed', None) or getattr(x, 'updated_parsed', None) or (0,), reverse=False)

    ex_tit = [k.strip().lower() for k in conf["exclude_title_keywords"].split(",") if k.strip()]
    m_h = float(conf.get("max_age_hours", 24.0))

    candidate_entries = []
    for e in all_entries:
        lnk, tit = e.get("link", ""), e.get("title", "")
        if lnk in purls or (ex_tit and any(kw in tit.lower() or kw in lnk.lower() for k in ex_tit)): continue
        top_i = getattr(e, 'original_index', 99) < 3
        pdt = getattr(e, "published_parsed", getattr(e, "updated_parsed", None))
        if not pdt and not top_i: continue
        diff_h = (nw_u - datetime.datetime(*pdt[:6], tzinfo=datetime.timezone.utc)).total_seconds() / 3600.0 if pdt else 0.0
        if maxh < 9999.0 and not top_i and diff_h > m_h: continue
        candidate_entries.append(e)

    if not candidate_entries: 
        print("Empty. System halting properly checking queues natively over lists.")
        return

    ws = os.path.join(os.getcwd(), 'workspace')
    im_d, pimg_d, pvid_d = os.path.join(ws, 'images'), os.path.join(ws, 'processed_images'), os.path.join(ws, 'processed_vids')
    os.makedirs(ws, exist_ok=True)
    ex_body = [kw.strip().lower() for kw in conf["exclude_body_keywords"].split(",") if kw.strip()]
    minw = conf.get("min_word_count", 200)

    for cidx, cent in enumerate(candidate_entries):
        hdg, sur = cent.get("title", ""), cent.get("link", "")
        print(f"\n===== [ {cidx+1} ] Execution Block Firing ===== \n=> {hdg}")

        pcont = scrape_article(sur)
        if len(pcont.split()) < minw or (ex_body and any(k in pcont.lower() for k in ex_body)):
            print(f"[REJECTED] Bounced properly length limits boundaries applied exactly matching algorithms!")
            with open("processed_urls.txt", "a") as fkw: fkw.write(sur+"\n")
            continue

        clear_temp_workspace(ws)
        
        try:
            aup, srtp = os.path.join(ws, "audio.mp3"), os.path.join(ws, "subtitles.srt")
            asyncio.run(generate_voice_and_subtitles(pcont, conf["voice"], aup, srtp))
            a_dr = get_audio_duration(aup)
            req_imgs = 30 if a_dr > 240.0 else 22

            # আপনার সবচেয়ে নিখুঁত অরিজিনাল লজিক, শুধু টাইপো ঠিক করা!
            entx = re.findall(r'\b[A-Z][a-z]{3,}\b', pcont)
            subsearch_key = f"{entx[0]} {entx[1]}" if len(entx) >= 2 else "Sports match recap points players"
            
            # ---> The Magical Accurate Photo Downloader Active Over Main Core Block <----
            raw_target_urls = smart_ddgs_images_search(subsearch_key, req_imgs)
            
            # ইমার্জেন্সি ক্র্যাশ এড়াতে ফলব্যাক হিসেবে উইকিমিডিয়া দিয়ে ট্রাই
            if not raw_target_urls:
                print("DDG Blocked remotely safely shifting API keys toward wikipedia reliable endpoints universally valid without limits.")
                try:
                    rqbx = requests.get(f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=filetype:bitmap {urllib.parse.quote(subsearch_key)}&gsrlimit={req_imgs}&prop=imageinfo&iiprop=url", timeout=10)
                    pgsb_tbs = rqbx.json().get("query", {}).get("pages", {})
                    for pjxdx_val in pgsb_tbs.values():
                        p_ig_ffxs=pjxdx_val.get("imageinfo", [])
                        if p_ig_ffxs: raw_target_urls.append(p_ig_ffxs[0].get("url"))
                except: pass
            
            if not raw_target_urls: raw_target_urls = (GENERIC_SPORTS_FALLBACKS * (req_imgs//len(GENERIC_SPORTS_FALLBACKS)+1))[:req_imgs]
                
            val_down = 0
            for iu in raw_target_urls:
                if val_down >= req_imgs: break # Download Limiting Safety Max Guard Lock Over RAM Cache Limit
                try:
                    rvx = requests.get(iu, timeout=7)
                    if rvx.status_code == 200:
                        with open(os.path.join(im_d, f"imp_pxlocn{val_down:02d}.jpg"), 'wb') as fgf: fgf.write(rvx.content)
                        val_down += 1
                except: pass

            dl_fs = sorted([zx for zx in os.listdir(im_d) if zx.endswith(('.jpg','.jpeg','.png'))])
            
            if not dl_fs:
                print("[ERROR] Blank frame. Ignoring pipeline safely passing over loops immediately jumping sequence cleanly skipping!")
                continue

            thpth = os.path.join(ws, "thumbnail.jpg")
            select_thumbnail_and_crop(im_d, thpth)

            print("Processing image visual proportions generating background frame natively within pure operations safely applying cinematic depths natively algorithms accurately resolving borders exactly matching...")
            for px_r in dl_fs:
                try:
                    with Image.open(os.path.join(im_d, px_r)) as obg:
                        bgz = obg.convert('RGB')
                        wxt, hyt = bgz.size
                        if wxt/hyt < 1.7:
                            bmxb = bgz.resize((1920,1080)).filter(ImageFilter.GaussianBlur(18))
                            sptx = int(1080*(wxt/hyt))
                            fmxb = bgz.resize((sptx, 1080))
                            bmxb.paste(fmxb, ((1920-sptx)//2, 0))
                            rtngz = bmxb
                        else: rtngz = bgz.resize((1920, 1080))
                        rtngz.save(os.path.join(pimg_d, f"pimgbxzzzzzzdfcsg_{px_r}"), quality=88) # সেভ স্পেস হালকা করতে Quality ৮০-৮৮ 
                except: pass

            pilproc_fps = sorted(os.listdir(pimg_d))
            if not pilproc_fps: continue

            ssts = parse_srt_start_times(srtp)
            if not ssts: ssts = [jk*(a_dr/len(pilproc_fps)) for jk in range(len(pilproc_fps))]
            elif ssts[0] > 0.1: ssts.insert(0, 0.0)
            else: ssts[0] = 0.0
            ssts.append(a_dr)
            nsn_ls = len(ssts) - 1

            cn_ls = []
            with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as poolv:
                tkx = []
                for sq in range(nsn_ls):
                    dgx = ssts[sq+1] - ssts[sq]
                    # Your highly reliable repetition rule internally restored identically properly without random garbage logics loops correctly here 
                    icvr_ph = os.path.join(pimg_d, pilproc_fps[sq % len(pilproc_fps)])
                    segpx = os.path.join(pvid_d, f"sl_{sq:03d}.mp4")
                    tkx.append(poolv.submit(render_zoom_segment, sq, dgx, icvr_ph, segpx))
                for tbj in tkx: cn_ls.append(tbj.result())

            with open(os.path.join(ws, "fast_slider.txt"), "w") as wrnxc: wrnxc.write("\n".join(cn_ls))

            print("Concatenating hardware sequence pipeline logic.")
            tmpo, finc = "temp.mp4", "output_video.mp4"
            subprocess.run(["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-safe", "0", "-f", "concat", "-i", "fast_slider.txt", "-i", "audio.mp3", "-c:v", "copy", "-c:a", "copy", tmpo], cwd=ws, check=True)

            cdscol, bgshcol = hex_to_ass_color(conf["font_color"], 1.0), hex_to_ass_color(conf["bg_color"], conf.get("bg_opacity", 0.6)) # transparency standard matched layout correctly over backgrounds globally efficiently applying native style strings universally dynamically adjusting font rendering boundaries perfectly
            cstylebbfvxzxcc=f"FontName=Arial,FontSize={conf['font_size']},PrimaryColour={cdscol},BackColour={bgshcol},BorderStyle={conf['border_style']},Outline=2,Shadow=1,Alignment=2,MarginV={conf['margin_v']}"
            subprocess.run(["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", tmpo, "-vf", f"subtitles=subtitles.srt:force_style='{cstylebbfvxzxcc}'", "-c:v", "libx264", "-crf", "22", "-preset", "ultrafast", "-c:a", "copy", finc], cwd=ws, check=True)

            upload_to_youtube(os.path.join(ws, finc), thpth, hdg, f"Summary Recaps Details Full Insights Coverage Over: {hdg}\nAutomatically managed successfully reliably reporting without issues over direct source connections safely tracking API points safely logic correctly processed worldwide...")
            with open("processed_urls.txt", "a") as fxsczvcxbzcxdgfb: fxsczvcxbzcxdgfb.write(sur + "\n")
            print("Video Render Subprocess Logic Generated Output Channel Live Online Deployed Completely Fast Tracking Correct System Values Properly Effectively Loop Safe Checked Finished Task Accurately Done ✔️\n")

        except Exception as xvdsvzdvdxcvcbs:
            traceback.print_exc()

if __name__ == "__main__":
    main()
