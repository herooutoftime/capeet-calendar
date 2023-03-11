from icalendar import Calendar, Event, vText, vCalAddress
from datetime import datetime, timedelta
import os
from pprint import pprint
import re
from bs4 import BeautifulSoup, PageElement, ResultSet, Tag
from flask import Flask
import requests
import markdownify
import config

def fetch(url: str) -> str:
    cached_gigs = "local/" + url.rsplit('/', 1)[-1] + ".cache"
    if (os.path.isfile(cached_gigs)):
        return open(cached_gigs).read()
    resp = requests.get(url)
    save(cached_gigs, resp.text)
    return resp.text

def save(filename: str, content, binary: bool = False):
    mode = "wb" if binary else "w"
    with open(filename, mode) as f:
        f.write(content)
        f.close()

def parse(contents: str):
    pattern = re.compile("(\d{2}.\d{2}.): <b>(.*?)</b> @ <i>(.*?)</i>(.*?)$", re.MULTILINE)
    matches = re.findall(pattern, contents)
    return matches

def is_cancelled(wrapped: str) -> bool:
    pattern = re.compile("cancelled\.")
    return False if pattern.search(wrapped) is None else True

def extract_bands(wrapped) -> str:
    regex = "<a[^>]*>([^<]+)<\/a>"
    pattern = re.compile(regex)
    if pattern.match(wrapped) is None:
        out = ", ".join(wrapped)
    else:
        matches = re.findall(pattern, wrapped)
        out = ", ".join(matches)
    return markdownify.markdownify(out, heading_style="ATX")

def extract_description(wrapped: str):
    return markdownify.markdownify(wrapped, heading_style="ATX")

def get_organizer(location: str):
    organizer = vCalAddress("test@test.at")
    organizer.params['cn'] = vText(location)
    return organizer   

def generate(gigs: list) -> Calendar:
    cal = Calendar()
    cal.add('prodid', '-//Deine Mudda//NONSGML Capeet Gig Calendar//DE')
    cal.add('version', '2.0')
    calendar_name = "Capeet Gig Calendar"
    cal.add("name", calendar_name)
    cal.add("X-WR-CALNAME", calendar_name)
    cal.add("X-WR-CALDESC", "Capeet would like to remind you that circle pits run counter clockwise...")
    cal.add("X-WR-TIMEZONE", "Europe/Vienna")
    cal.add("X-PUBLISHED-TTL", "PT12H")
    
    for gig in gigs:
        startdate = datetime.strptime(gig[0] + str(datetime.now().year), "%d.%m.%Y")
        enddate = startdate + timedelta(days=1)
        event = Event()
        event.add("dtstart", startdate)
        event.add("dtend", enddate)
        # event.add("organizer", get_organizer(gig[2]))
        event.add("status", "CANCELLED" if is_cancelled(gig[3]) else "TENTATIVE")
        summary = extract_bands(gig[1])
        if is_cancelled(gig[3]):
            summary = "!!! CANCELLED !!! " + summary
        event.add("summary", summary)
        event.add("location", vText(gig[2]))
        event.add("description", extract_description(gig[1]+ gig[3]))
        cal.add_component(event)

    return cal

app = Flask(__name__)
app.config.from_object(config.Config)
@app.route("/")
def index():
    remoteHtml = fetch(app.config["CAPEET_GIGLIST_URL"])
    extracted_gigs = parse(remoteHtml)
    icalendar = generate(extracted_gigs)
    return icalendar.to_ical()