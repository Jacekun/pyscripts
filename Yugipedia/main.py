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
MAX_SET_TO_PROCESS = 5
NEWLINE = '\n'
DELAY_SETLIST = 2
DELAY_PASSCODE = 1
BANLIST_FORMAT = "Yu-Gi-Oh! AE"
BANLIST_TITLE = "2023.11 OCG-AE"
LINE_BREAK = "==================================================================================================="

# Index
INDEX_SETCODE = 0
INDEX_NAME = 1
INDEX_JAP_NAME = 2
INDEX_RARITY = 3
INDEX_CATEGORY = 4
# Index if no JAP name on table.
INDEX_RARITY_NOJP = 2
INDEX_CATEGORY_NOJP = 3

# Links and Prefix
LINK_MAIN = "https://yugipedia.com"
LINK_WIKI = LINK_MAIN + "/wiki/"
PREFIX_CARDLIST = "Set_Card_Lists:"
SUFFIX_AE = "(Asian-English)"

INPUT_URL = "https://yugipedia.com/index.php?title=Special:Ask&limit=500&offset=0&q=%5B%5BMedium%3A%3AOfficial%5D%5D++%3Cq%3E+%3Cq%3E%5B%5BAsian-English+set+prefix%3A%3A%2B%5D%5D%3C%2Fq%3E++OR++%3Cq%3E%5B%5BAsian-English+release+date%3A%3A%2B%5D%5D%3C%2Fq%3E+%3C%2Fq%3E&p=mainlabel%3D-20Set%2Fformat%3Dtable%2Fheaders%3D-20plain%2Fclass%3D-20wikitable-20sortable-20card-2Dlist&po=%3FAsian-English+set+and+region+prefix%3DPrefix%0A%3FAsian-English+release+date%3DRelease+date%0A&sort=+Asian-English+release+date%2C+Asian-English+set+prefix%2C+%23&order=asc%2Casc%2Casc&eq=no#search"
URL_BANLIST_AE = "https://www.yugioh-card.com/hk/event/rules_guides/forbidden_cardlist_aen.php?list=202311&lang=en"

# File paths
FILE_OUTPUT_BODY = "body.html"
FILE_OUTPUT_DONE_SET = "setlist_done.log"# Already processed setcode prefix
FILE_OUTPUT_BANLIST = BANLIST_TITLE + ".lflist.conf"
FILE_CACHE_BANLIST = BANLIST_TITLE + ".html"
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
        if inputParsed.endswith(SUFFIX_AE):
            return f"{LINK_WIKI}{PREFIX_CARDLIST}{inputParsed.removesuffix(SUFFIX_AE)}({formatParsed})"
        else:
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

def load_dict_from_json(filename: str) -> dict[str, int]:
    # Load contents from file
    jsobObj = Utils.read_json(filename)
    dictReturn = { }

    if jsobObj:
        for item in jsobObj:
            setCode = str(item["set_number"]).strip().upper()
            passCode = int(item["passcode"])
            dictReturn[setCode] = passCode

        return dictReturn
    
    return None

def save_cardlist_to_json(outputFileSet: str, outputListCardData: list[CardData]) -> bool:
    Utils.log(f"Saving Card List to JSON file => {outputFileSet}")
    dumpListToDict = []
    for itemListCardData in outputListCardData:
        newItemDict = itemListCardData.model_dump(mode="dict")# IMPT! Convert data to format that can be serialized.
        dumpListToDict.append(newItemDict)

    resultSuccess = Utils.write_json(outputFileSet, dumpListToDict)
    if resultSuccess:
        Utils.log(f"Successfully created json file.")
        return True
    
    return False

def filter_list_unique_set(cardList: list[CardData]) -> list[CardData]:
    Utils.log(f"Filtering list..")
    returnList: list[CardData] = []
    listAlreadyExist: list[str] = []

    for item in cardList:
        if item.set_number in listAlreadyExist:
            pass
        else:
            listAlreadyExist.append(item.set_number)
            returnList.append(item)

    return returnList

def process_setlist(inputString: str, filename: str, listCardItems: list[CardData]) -> bool:
    # Vars
    count = 0

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
        setReleaseDateEpoch: float = 0
        if setReleaseDateEl is not None:
            if len(setReleaseDateEl) >= 3:
                setReleaseDate = setReleaseDateEl[2].text.replace("Release date:", "").replace("(", "").replace(")", "").strip()
                setReleaseDateEpoch = Utils.string_to_datetime(setReleaseDate).timestamp()

        Utils.log(f"Set list page => Release date: {setReleaseDate}")
        
        soupListMain = soupObj.find_all("div", { "class": "set-list" })
        if not soupListMain:
            raise Exception("Set list page => 'div' with class 'set-list' not found.")
        
        for soupItemMain in soupListMain:
            soupListMainElem = soupItemMain.find_all("tr")
            if not soupListMainElem:
                raise Exception("Set list page => 'tr' element not found.")

            dictAlreadyExist = load_dict_from_json(filename)
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
                    cardPasscode = 0

                    if dictAlreadyExist:
                        if cardSetcode in dictAlreadyExist:
                            cardPasscode = dictAlreadyExist[cardSetcode]
                            Utils.log(f"Set list page => Use cached passcode from existing json file. Passcode: {cardPasscode}")

                    if cardPasscode == 0:
                        cardPasscode = get_card_passcode(cardUrl)

                    if lenSoupListProp > 5:
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
                            rarity =  "", 
                            date_release = setReleaseDate,
                            date_release_epoch = setReleaseDateEpoch
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
                                date_release = setReleaseDate,
                                date_release_epoch = setReleaseDateEpoch
                            )
                            listCardItems.append(cardItem)

                    Utils.log(f"Item => Setcode: {cardSetcode} | URL: {cardUrl} | Name: {cardName}")
                    Utils.log(LINE_BREAK)

                    time.sleep(DELAY_PASSCODE) # Throttle process to prevent overloading website.
            ##
    elif reqMain.status_code == 404:
        Utils.log(f"Page not found. Will skip.")
    else:
        raise Exception(f"Cannot download page: {inputString}. Code: {reqMain.status_code}")
    
    return True

def process_banlist():
    banlistContents: str = f"#[{BANLIST_FORMAT} {BANLIST_TITLE}]\n!{BANLIST_TITLE}\n$whitelist\n"
    banlistCardDict = { }
    filesToProcess = Utils.list_files(FOLDER_OUTPUT)
    listLimitBanned = []

    # First, get the banlist and process it
    contentsHtml: str = "<div></div>"#Placeholder that can be parsed by BSoup
    if not os.path.exists(FILE_CACHE_BANLIST):
        reqObj = requests.get(url = URL_BANLIST_AE, headers = HEADERS)
        if reqObj.ok:
            contentsHtml = reqObj.text
            Utils.write_file(FILE_CACHE_BANLIST, contentsHtml)
    else:
        contentsHtml = Utils.read_file(FILE_CACHE_BANLIST)
    
    if contentsHtml:
        Utils.log(f"Banlist => Content exist")
        soupObj: BeautifulSoup = None

        if not contentsHtml.isspace():
            soupObj = BeautifulSoup(contentsHtml, "html.parser")

        if soupObj:
            Utils.log(f"Banlist => Main element exist")
            soupMain = soupObj.find("table", { "class": "limit_list_style" } )
            if soupMain:
                Utils.log(f"Banlist => Main table exist")
                soupMainBody = soupMain.find("tbody")
                if soupMainBody:
                    Utils.log(f"Banlist => Main table body exist")
                    soupMainCardList = soupMainBody.find_all("tr")
                    if soupMainCardList:
                        Utils.log(f"Banlist => Element list of Card names found")
                        for soupItem in soupMainCardList:
                            if soupItem:
                                soupCardName = soupItem.find("td")
                                #Utils.log(f"Banlist => Element 'td' found on item.")
                                if soupCardName:
                                    cardName: str = soupCardName.text
                                    Utils.log(f"Card Name => {cardName}")
                                    listLimitBanned.append(cardName)
    #raise Exception("dummy test")

    for x in filesToProcess:
        Utils.log(f"File => {x}")
        jsonObj = Utils.read_json(x)
        if jsonObj:
            Utils.log(f"JSON file parsed.")
            cardDataList = CardData.get_list_carddata(jsonObj)
            Utils.log("CardData processed.")
            for card in cardDataList:
                cardPasscode: int = card.passcode
                cardName: str = card.name
                cardSetNumber: str = card.set_number
                if cardPasscode in banlistCardDict:
                    Utils.log(f"Card already exist => {cardPasscode} | name: {cardName}")
                else:
                    banlistCardDict[cardPasscode] = {
                        "name": cardName,
                        "setcode": cardSetNumber
                    }
                    Utils.log(f"Card info => {cardPasscode} | name: {cardName}")
        else:
            Utils.log("JSON file parsing failed!")

    # Create conf whitelist file
    if banlistCardDict:
        for key in banlistCardDict:
            if key and key != 0 :
                item = banlistCardDict[key]
                qty: int = 3
                cardName: str = str(item["name"])

                # Check qty
                if cardName in listLimitBanned:
                    qty = 0
                    Utils.log(f"Card is banned => {cardName}")

                if qty > 0:
                    contentToWrite: str = f"{key} {qty} # {cardName}"
                    banlistContents += contentToWrite + "\n"
                    Utils.log(f"Card to write => {contentToWrite}")
        # Create output file
        Utils.write_file(FILE_OUTPUT_BANLIST, banlistContents)

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
        
        lenSetContentList = len(setContentList)
        
        Utils.log("Parsing Set 'Name' and 'Link'..")
        setNameLink = setContentList[0].find("a")
        
        setNameList = setNameLink.text.split()
        setName = ' '.join(setNameList).strip()
        
        setLink: str = setNameLink["href"]
        setLinkProper: str = LINK_MAIN + setLink
        setLinkWithCardSetList: str = get_setlist_from_wikilink(setLinkProper, "OCG-AE")
        setPrefix: str = ""
        setReleaseDate: datetime = None
        setReleaseDateRaw: str = ""

        if lenSetContentList >= 2:
            setContentObj = setContentList[1]
            if setContentObj:
                setPrefix = setContentObj.text.strip().upper()
        
        if lenSetContentList >= 3:
            setContentObj = setContentList[2]
            if setContentObj:
                setReleaseDateRaw = setContentObj.text.strip()
                setReleaseDate = Utils.string_to_datetime(setReleaseDateRaw)
        
        if setPrefix.isspace():
            Utils.log(f"Skipped : {setLinkProper}")
        else:
            if setPrefix in LIST_DONESET:
                Utils.log(f"Prefix: {setPrefix} is skipped. Already processed.\n{LINE_BREAK}")
                LIST_DONESET.remove(setPrefix)
            else:
                #Utils.log(f"Prefix: {setPrefix} | Set URL: {setLinkWithCardSetList}")

                # Skip unreleased setlist
                if setReleaseDate is None:
                    Utils.log(f"Skipped : Set '{setPrefix}' has no release date. Raw: {setReleaseDateRaw}")
                    continue
                    
                if setReleaseDate.date() > datetime.now().date():
                    Utils.log(f"Skipped : Set '{setPrefix}' is still unreleased. Release date: {setReleaseDate.date()}")
                    continue

                Utils.log(f"Set '{setPrefix}' Release date => Raw: {setReleaseDateRaw} | Converted: {setReleaseDate}")
                outputFileSet = os.path.join(FOLDER_OUTPUT, f"AE_{setPrefix}.json")
                outputListCardData: list[CardData] = []
                successCardList = False
                try:
                    successCardList = process_setlist(setLinkWithCardSetList, outputFileSet, outputListCardData)
                except Exception as e:
                    Utils.log_err("Parse list, main", e)
                    successCardList = False

                # Save output even if not succes, for cache
                if outputListCardData:
                    Utils.log(f"Creating output json file for set '{setPrefix}' => {outputFileSet}")
                    #outputListCardDataFiltered = filter_list_unique_set(outputListCardData)
                    resultSuccess = save_cardlist_to_json(outputFileSet, outputListCardData)
                    if resultSuccess:
                        count += 1
                        # Save prefix only if all cards from setlist is processed.
                        if successCardList:
                            Utils.append_file(FILE_OUTPUT_DONE_SET, f"{NEWLINE}{setPrefix}")
                        else:
                            Utils.log(f"Failed to parse Set list with prefix '{setPrefix}'. Check logs.")
                            #raise Exception(f"Failed to parse Set list with prefix '{setPrefix}'. Check logs.")
                    
                    outputListCardData.clear()

                Utils.log(LINE_BREAK)
                time.sleep(DELAY_SETLIST) # Throttle process to prevent overloading website.
        
        if count == MAX_SET_TO_PROCESS:
            break

    #Process whitelist for EDOPro when all setlists are done.
    process_banlist()

except Exception as e:
    Utils.log_err("Error, main", e)
finally:
    TIME_END = time.time() - TIME_START
    if TIME_END > 60:
        Utils.log(f"Elapsed minutes: {TIME_END/60}")
    else:
        Utils.log(f"Elapsed seconds: {TIME_END}")
