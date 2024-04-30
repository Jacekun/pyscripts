import requests
import os
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# Import local files
from data.utils import Utils
from data.model_card import CardData

# Timer for processing
TIME_START = time.time()

# Global constants
MAX_SET_TO_PROCESS = 4
NEWLINE = '\n'
DELAY_SETLIST = 3
DELAY_PASSCODE = 1

# Index
INDEX_SETCODE = 0
INDEX_NAME = 1
INDEX_JAP_NAME = 2
INDEX_RARITY = 3
INDEX_CATEGORY = 4
# Index if no JAP name on table.
INDEX_RARITY_NOJP = 2
INDEX_CATEGORY_NOJP = 3

LINK_MAIN = "https://yugipedia.com"
LINK_WIKI = LINK_MAIN + "/wiki/"
PREFIX_CARDLIST = "Set_Card_Lists:"

INPUT_URL = "https://yugipedia.com/index.php?title=Special:Ask&limit=500&offset=0&q=%5B%5BMedium%3A%3AOfficial%5D%5D++%3Cq%3E+%3Cq%3E%5B%5BAsian-English+set+prefix%3A%3A%2B%5D%5D%3C%2Fq%3E++OR++%3Cq%3E%5B%5BAsian-English+release+date%3A%3A%2B%5D%5D%3C%2Fq%3E+%3C%2Fq%3E&p=mainlabel%3D-20Set%2Fformat%3Dtable%2Fheaders%3D-20plain%2Fclass%3D-20wikitable-20sortable-20card-2Dlist&po=%3FAsian-English+set+and+region+prefix%3DPrefix%0A%3FAsian-English+release+date%3DRelease+date%0A&sort=+Asian-English+release+date%2C+Asian-English+set+prefix%2C+%23&order=asc%2Casc%2Casc&eq=no#search"#TODO: Proper INPUT_URL parsing

# File paths
FILE_OUTPUT_BODY = "body.html"
FILE_OUTPUT_DONE_SET = "setlist_done.log"# Already processed setcode prefix
FOLDER_OUTPUT = "output"#Folder to save all json files per set

# List objects
LIST_DONESET = []

# Global variables
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Origin': LINK_MAIN,
    'Referer': LINK_MAIN,
    "Content-Type": "text/html",
}

# Methods
def get_setlist_from_wikilink(inputString: str, format: str) -> str:
    formatParsed = "OCG-JP"

    if not inputString or inputString.isspace():
        raise Exception("Invalid wikilink : Empty string")

    if not format or format.isspace():
        formatParsed = "OCG-JP"
    else:
        formatParsed = format.strip().upper()
    
    inputParsed = inputString[len(LINK_WIKI):]
    if not inputParsed.startswith(PREFIX_CARDLIST):
        return f"{LINK_WIKI}{PREFIX_CARDLIST}{inputParsed}_({formatParsed})"

    return inputString

def get_card_passcode(wikilink: str) -> int:
    cardPasscode: int = 0
    if wikilink:
        Utils.log(f"Searching passcode for {wikilink}")
        reqMain = requests.get(url = wikilink, headers = HEADERS)
        if reqMain.ok:
            Utils.log("Passcode => Page downloaded. Parsing content")
            soupObj = BeautifulSoup(reqMain.text, "html.parser")
            if not soupObj:
                raise Exception("Passcode => Content not found.")
        
            soupOtherInfo = soupObj.find("table", { "class": "innertable" } )
            if not soupOtherInfo:
                raise Exception("Passcode => 'table' element not found.")
            
            soupOtherInfoTr = soupOtherInfo.find_all("tr")
            if not soupOtherInfoTr:
                raise Exception("Passcode => 'tr' in 'table' element not found.")
            
            for otherInfoEl in soupOtherInfoTr:
                otherElTh = otherInfoEl.find("th")
                otherElTd = otherInfoEl.find("td")
                if not otherElTh or not otherElTd:
                    continue
                
                otherInfoName: str = otherElTh.text.replace("/", "").strip().upper()
                otherInfoValue: str = otherElTd.text.strip()
                Utils.log(f"Passcode => Item: {otherInfoName} | {otherInfoValue}")

                if otherInfoName == "PASSWORD":
                    if otherInfoValue.isdecimal():
                        cardPasscode = int(otherInfoValue)
                    else:
                        Utils.log(f"Passcode => Invalid value.")
                    break

    return cardPasscode

def process_setlist(inputString: str) -> list[CardData]:
    # Vars
    count = 0
    listCardItems = []

    # Get page
    reqMain = requests.get(url = inputString, headers = HEADERS)

    # Parse response
    Utils.log(f"Processing page => {inputString}")
    if reqMain.ok:
        content = reqMain.text.strip()

        soupObj = BeautifulSoup(content, "html.parser")
        if not soupObj:
            raise Exception("Set list page => Content not found.")

        setReleaseDateEl = soupObj.find("div", { "class": "page-header" } ).find_all("div")
        setReleaseDate: str = ""
        if setReleaseDateEl is not None:
            if len(setReleaseDateEl) >= 3:
                setReleaseDate = setReleaseDateEl[2].text.replace("Release date:", "").replace("(", "").replace(")", "").strip()

        Utils.log(f"Set list page => Release date: {setReleaseDate}")
        
        soupListMain = soupObj.find("div", { "class": "set-list" })
        if not soupListMain:
            raise Exception("Set list page => 'div' with class 'set-list' not found.")

        soupListMainElem = soupListMain.find_all("tr")
        if not soupListMainElem:
            raise Exception("Set list page => 'tr' element not found.")

        for soupItem in soupListMainElem:
            soupItemListProp = soupItem.find_all("td")
            
            if soupItemListProp:    
                lenSoupListProp: int = len(soupItemListProp)
                
                cardUrlElemA = soupItemListProp[INDEX_SETCODE].find("a")
                if not cardUrlElemA:
                    raise Exception("Set list page => 'a' element not found for Card URL.")

                cardUrl = cardUrlElemA["href"]
                cardUrl = cardUrl if cardUrl.startswith(LINK_MAIN) else LINK_MAIN + cardUrl
                cardSetcode = cardUrlElemA.text.strip().upper()
                cardName = soupItemListProp[INDEX_NAME].find("a").text.strip()
                cardNameJap = ""
                cardCategory = ""
                cardRaritiesElem = None
                cardPasscode = get_card_passcode(cardUrl)

                if lenSoupListProp >= 5:
                    cardNameJap = soupItemListProp[INDEX_JAP_NAME].text.strip()
                    cardCategory = soupItemListProp[INDEX_CATEGORY].text.strip()
                    cardRaritiesElem = soupItemListProp[INDEX_RARITY]
                else:
                    cardCategory = soupItemListProp[INDEX_CATEGORY_NOJP].text.strip()
                    cardRaritiesElem = soupItemListProp[INDEX_RARITY_NOJP]

                if not cardRaritiesElem:
                    cardItem = CardData(
                        name = cardName, 
                        passcode = cardPasscode,
                        wikilink = cardUrl, 
                        set_number = cardSetcode,
                        rarity =  "Normal", 
                        date_release = setReleaseDate
                    )
                    listCardItems.append(cardItem)
                else:
                    for cardRarityEl in cardRaritiesElem:
                        cardRarity = cardRarityEl.text.strip()
                        cardItem = CardData(
                            name = cardName, 
                            passcode = cardPasscode,
                            wikilink = cardUrl, 
                            set_number = cardSetcode,
                            rarity =  cardRarity, 
                            date_release = setReleaseDate
                        )
                        listCardItems.append(cardItem)

                Utils.log(f"Item => Setcode: {cardSetcode} | URL: {cardUrl} | Name: {cardName}")
                Utils.log(f"===================================================================================================")

                time.sleep(DELAY_PASSCODE) # Throttle process to prevent overloading website.
        ##
    elif reqMain.status_code == 404:
        Utils.log(f"Page not found. Will skip.")
    else:
        raise Exception(f"Cannot download page: {inputString}. Code: {reqMain.status_code}")
    
    return listCardItems

# Main
try:
    # Create folders
    Path(FOLDER_OUTPUT).mkdir(parents=True, exist_ok=True)

    # Clear old log files
    Utils.clear_logs()

    # Check URL
    if INPUT_URL is None or INPUT_URL == "":
        raise Exception("Invalid INPUT_URL : Blank or null.")

    # Request page and cache it, or load cached data.
    if not os.path.exists(FILE_OUTPUT_BODY):
        reqMain = requests.get(url = INPUT_URL, headers = HEADERS)
        if reqMain.ok:
            CONTENTS_HTML = reqMain.text
            Utils.write_file(FILE_OUTPUT_BODY, CONTENTS_HTML)
        else:
            raise Exception(f"Page not downloaded, status code: {reqMain.status_code}")
    else:
        # Open cached file
        CONTENTS_HTML = Utils.read_file(FILE_OUTPUT_BODY).strip()

    # Load already done sets
    LIST_DONESET_FROMFILE = Utils.read_file(FILE_OUTPUT_DONE_SET).split()
    for doneSetItem in LIST_DONESET_FROMFILE:
        doneSetItemProper = doneSetItem.strip().upper()
        Utils.log(f"Set '{doneSetItemProper}' is already processed.")
        LIST_DONESET.append(doneSetItemProper)

    if CONTENTS_HTML != "":
        Utils.log("File loaded successfully")

    Utils.log("Parsing soup...")
    soupObj = BeautifulSoup(CONTENTS_HTML, "html.parser")

    Utils.log("Finding main body from html...")
    soupMain = soupObj.find("div", { "id": "result" } )
    if soupMain is None:
        raise Exception("Main body not found => id: result")
    
    Utils.log("Parsing setlist...")
    soupSetList = soupMain.find_all("tr")
    if soupSetList is None:
        raise Exception("Set list not found => tr")

    count = 0
    for soupSetItem in soupSetList:
        setContentList = soupSetItem.find_all("td")
        if setContentList is None:
            raise Exception("Set is not parsable.")
        
        setNameLink = setContentList[0].find("a")
        
        setNameList = setNameLink.text.split()
        setName = ' '.join(setNameList).strip()
        
        setLink = setNameLink["href"]
        setLinkProper = LINK_MAIN + setLink
        setLinkWithCardSetList = get_setlist_from_wikilink(setLinkProper, "OCG-AE")

        setPrefix = setContentList[1].text.strip().upper()
        
        if not setPrefix or setPrefix.isspace():
            Utils.log(f"Skipped : {setLinkProper}")
        else:
            if setPrefix in LIST_DONESET:
                Utils.log(f"Prefix: {setPrefix} is skipped. Already processed.")
                LIST_DONESET.remove(setPrefix)
            else:
                #Utils.log(f"Prefix: {setPrefix} | Set URL: {setLinkWithCardSetList}")
                listCardData = process_setlist(setLinkWithCardSetList)
                if listCardData:
                    outputFileSet = os.path.join(FOLDER_OUTPUT, f"{setPrefix}_AE.json")
                    Utils.log(f"Creating output json file for set '{setPrefix}' => {outputFileSet}")

                    dumpListToDict = []
                    for itemListCardData in listCardData:
                        newItemDict = itemListCardData.model_dump(mode="dict")# IMPT! Convert data to format that can be serialized.
                        dumpListToDict.append(newItemDict)

                    resultSuccess = Utils.write_json(outputFileSet, dumpListToDict)
                    if resultSuccess:
                        Utils.log(f"Successfully created json file.")
                        Utils.append_file(FILE_OUTPUT_DONE_SET, f"{NEWLINE}{setPrefix}")
                        count += 1
                
                time.sleep(DELAY_SETLIST) # Throttle process to prevent overloading website.
        
        if count == MAX_SET_TO_PROCESS:
            break

except Exception as e:
    Utils.log_err("Error, main", e)
finally:
    TIME_END = time.time() - TIME_START
    if TIME_END > 60:
        Utils.log(f"Elapsed minutes: {TIME_END/60}")
    else:
        Utils.log(f"Elapsed seconds: {TIME_END}")
