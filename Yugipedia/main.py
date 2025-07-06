import os
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import curl_cffi

# Import local files
from data.utils import Utils
from data.model_card import CardData, CardInfo
from data.model_sets import WikiSet

# Timer for processing
TIME_START = time.time()

# Global constants
DEBUG = False
MAX_SET_TO_PROCESS = 7
NEWLINE = '\n'
DELAY_SETLIST = 2
DELAY_PASSCODE = 1
BANLIST_FORMAT = "Yu-Gi-Oh! AE"
BANLIST_TITLE = "2025.04 OCG-AE"
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

INPUT_URL = "https://yugipedia.com/index.php?title=Special:Ask&x=-5B-5BMedium%3A%3AOfficial-5D-5D-20-20-3Cq-3E-20-3Cq-3E-5B-5BAsian-2DEnglish-20set-20prefix%3A%3A%2B-5D-5D-3C-2Fq-3E-20-20OR-20-20-3Cq-3E-5B-5BAsian-2DEnglish-20release-20date%3A%3A%2B-5D-5D-3C-2Fq-3E-20-3C-2Fq-3E%2F-3FAsian-2DEnglish-20set-20and-20region-20prefix%3DPrefix%2F-3FAsian-2DEnglish-20release-20date%3DRelease-20date&mainlabel=Set&format=json&headers=+plain&class=+wikitable+sortable+card-list&sort=Asian-English+release+date%2CAsian-English+set+prefix%2C%23&order=asc%2Casc%2Casc&offset=0&limit=500&prettyprint=true&unescape=true"
#URL_BANLIST_AE = "https://www.yugioh-card.com/hk/event/rules_guides/forbidden_cardlist_aen.php?list=202501&lang=en"
URL_BANLIST_AE = "https://dawnbrandbots.github.io/yaml-yugi-limit-regulation/ocg-ae/current.vector.json"

# File paths
EXT_OUTPUT_BANLIST = ".lflist.conf"
FILE_OUTPUT_BODY = "result.json"
FILE_OUTPUT_DONE_SET = "setlist_done.log" # Already processed setcode prefix
FILE_OUTPUT_ERROR_SET = "setlist_error.log" # Set with an error
FILE_OUTPUT_BANLIST = "AE_Banlist" + EXT_OUTPUT_BANLIST
FILE_CACHE_BANLIST = BANLIST_TITLE + ".json"
FOLDER_OUTPUT = "output"#Folder to save all json files per set

# List objects
LIST_DONESET = []

# Global variables
HEADERS = {
    #'Accept': 'application/json',
    #'Accept-Encoding':'gzip, deflate, br',
    #'Accept-Language':'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Origin': LINK_MAIN,
    'Referer': LINK_MAIN,
    'Content-Type': 'application/json',
}

# Methods
def request_page(page: str, includeHeader: bool) -> any:
    Utils.log(f"Requesting page => { page }")
    if includeHeader:
        return curl_cffi.get(page, impersonate="firefox135", headers=HEADERS, timeout=50)
    else:
        return curl_cffi.get(page, impersonate="firefox135", timeout=50)

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

def get_card_passcode(wikilink: str) -> CardInfo:
    cardPasscode: int = 0
    cardKonamiId: int = 0
    if wikilink:
        Utils.log(f"Searching passcode for {wikilink}")
        reqMain = request_page(wikilink, False)
        if reqMain.ok:
            Utils.log("Passcode => Page downloaded. Parsing content")
            soupObj = BeautifulSoup(reqMain.text, "html.parser")
            if not soupObj:
                raise Exception("Passcode => Content not found.")
            
            soupKonamiIdDiv = soupObj.find("div", { "class": "below hlist plainlinks" })
            if soupKonamiIdDiv:
                soupKonamiIdText = soupKonamiIdDiv.find("li")
                if soupKonamiIdText:
                    #Utils.log(f"Parse Konami Id, contents => { soupKonamiIdText }")
                    tempKonamiIdRawList = soupKonamiIdText.get_text().strip().split("#")
                    if tempKonamiIdRawList:
                        textKonamiIdIndex: int = 1 if len(tempKonamiIdRawList) > 1 else 0
                        textKonamiIdRaw: str = tempKonamiIdRawList[textKonamiIdIndex].strip()
                        textKonamiId: str = textKonamiIdRaw.split(None, 1)[0]
                        Utils.log(f"Parse Konami Id, contents => Index: { textKonamiIdIndex } | Text: { textKonamiId } | Raw: { textKonamiIdRaw }")
                        if textKonamiId.isdecimal():
                            cardKonamiId = int(textKonamiId)
                        else:
                            Utils.log(f"Parse Konami Id, contents => Invalid value: { textKonamiId }")
                    else:
                        raise Exception(f"Parse Konami Id, contents => No valid text after # in tag text.")
                else:
                    raise Exception("Parse Konami Id, contents => Null, not found 'li' tag.")
            else:
                raise Exception("Parse Konami Id, contents => Null, not found 'div' class 'below hlist plainlinks'.")
        
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
                        Utils.log(f"Passcode => Invalid value: { otherInfoValue }")
                    break

    return CardInfo(
        passcode = cardPasscode,
        konami_id = cardKonamiId
    )

def load_dict_from_json(filename: str) -> dict[str, any]:
    # Load contents from file
    jsobObj = Utils.read_json(filename)
    dictReturn = { }

    if jsobObj:
        for item in jsobObj:
            setCode = str(item["set_number"]).strip().upper()
            passcode = int(item["passcode"])
            konami_id = int(item["konami_id"])
            dictReturn[setCode] = {
                "passcode": passcode,
                "konami_id": konami_id,
            }

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

def process_setlist(setFullName: str, inputString: str, filename: str, listCardItems: list[CardData]) -> bool:
    # Vars
    count = 0

    # Get page
    reqMain = request_page(inputString, False)

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
        isElementFound: bool = False
        if setReleaseDateEl is not None:
            for setReleaseDateElItem in setReleaseDateEl:
                if isElementFound:
                    break
                if setReleaseDateElItem:
                    setReleaseDateInnerDiv = setReleaseDateElItem.find_all("div")
                    if setReleaseDateInnerDiv is not None:
                        for setReleaseDateInnerDivItem in setReleaseDateInnerDiv:
                            rawString: str = setReleaseDateInnerDivItem.text.strip().upper()
                            #Utils.log(f"[Data] Release date => { rawString }")
                            if "RELEASE DATE:" in rawString:
                                setReleaseDate = rawString.replace("RELEASE DATE:", "").replace("(", "").replace(")", "").strip()
                                setReleaseDateEpoch = Utils.string_to_datetime(setReleaseDate).timestamp()
                                isElementFound = True
                                break
                

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
                    cardKonamiId = 0

                    if dictAlreadyExist:
                        if cardSetcode in dictAlreadyExist:
                            itemExist = dictAlreadyExist[cardSetcode]
                            cardPasscode = int(itemExist["passcode"])
                            cardKonamiId = int(itemExist["konami_id"])
                            Utils.log(f"Set list page => Use cached passcode from existing json file. Passcode: { cardPasscode } | Konami Id: { cardKonamiId }")

                    if lenSoupListProp > 5:
                        cardNameJap = soupItemListProp[INDEX_JAP_NAME].text.strip()
                        cardCategory = soupItemListProp[INDEX_CATEGORY].text.strip().upper()
                        cardRaritiesElem = soupItemListProp[INDEX_RARITY]
                    else:
                        cardCategory = soupItemListProp[INDEX_CATEGORY_NOJP].text.strip().upper()
                        cardRaritiesElem = soupItemListProp[INDEX_RARITY_NOJP]

                    # Skip tokens
                    if cardCategory == "TOKEN":
                        continue
                    
                    # Fetch passcode using URL
                    if cardPasscode == 0:
                        cardInfoObj = get_card_passcode(cardUrl)
                        cardPasscode = cardInfoObj.passcode
                        cardKonamiId = cardInfoObj.konami_id
                    
                    # Build JSON object item
                    if not cardRaritiesElem:
                        cardItem = CardData(
                            name = cardName, 
                            passcode = cardPasscode,
                            konami_id = cardKonamiId,
                            wikilink = cardUrl, 
                            set_number = cardSetcode,
                            set_name = setFullName,
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
                                konami_id = cardKonamiId,
                                wikilink = cardUrl, 
                                set_number = cardSetcode,
                                set_name = setFullName,
                                rarity =  cardRarity, 
                                date_release = setReleaseDate,
                                date_release_epoch = setReleaseDateEpoch
                            )
                            listCardItems.append(cardItem)

                    Utils.log(f"Item => Setcode: {cardSetcode} | URL: {cardUrl} | Name: {cardName} | Category: {cardCategory}")
                    Utils.log(LINE_BREAK)

                    time.sleep(DELAY_PASSCODE) # Throttle process to prevent overloading website.
            ##
    elif reqMain.status_code == 404:
        Utils.log(f"[Error] Page not found. Will skip.")
    else:
        raise Exception(f"Cannot download page: {inputString} \n Code: {reqMain.status_code}")
    
    return True

# Create banlist file.
def process_banlist():
    banlistContents: str = f"#[{BANLIST_FORMAT} {BANLIST_TITLE}]\n!{BANLIST_TITLE}\n$whitelist\n"
    banlistCardDict = { }
    filesToProcess = Utils.list_files(FOLDER_OUTPUT)
    listLimitBanned: list[tuple[int, int]] = []

    # First, get the banlist and process it
    dataBanlistJson: any = None
    if not os.path.exists(FILE_CACHE_BANLIST):
        reqObj = request_page(URL_BANLIST_AE, False)
        if reqObj.ok:
            contentsHtml = reqObj.text.strip()
            Utils.write_file(FILE_CACHE_BANLIST, contentsHtml)
    
    # read from file
    dataBanlistJson = Utils.read_json(FILE_CACHE_BANLIST)
    
    if dataBanlistJson:
        Utils.log(f"Banlist => Parsed JSON file.")
        objRegulations = dataBanlistJson["regulation"]
        if objRegulations:
            for dataKey, dataValue in objRegulations.items():
                cardKonamiId = int(dataKey)
                cardLimit = int(dataValue)
                banlistItem: tuple[int, int] = (cardKonamiId, cardLimit)
                listLimitBanned.append(banlistItem)
                Utils.log(f"Banlist, Limit Count => Konami Id: { cardKonamiId } | Limit: { cardLimit }")
        
    #raise Exception("dummy test")

    for x in filesToProcess:
        Utils.log(f"Banlist, Set File => Filename: { x }")
        jsonObj = Utils.read_json(x)
        if jsonObj:
            Utils.log("Banlist, Set File => JSON file parsed.")
            cardDataList = CardData.get_list_carddata(jsonObj)
            Utils.log("Banlist, Set File => CardData processed.")
            for card in cardDataList:
                cardPasscode: int = card.passcode
                cardKonamiId: int = card.konami_id
                cardName: str = card.name
                qty: int = 3
                if cardKonamiId in banlistCardDict:
                    pass #do nothing
                    #Utils.log(f"Card already exist => {cardPasscode} | name: {cardName}")
                else:
                    # Parse restriction limit for card.
                    banlistItemList = [item for item in listLimitBanned if cardKonamiId in item]
                    if banlistItemList:
                        banlistItemFirst = banlistItemList[0]
                        qty = banlistItemFirst[1]
                        listLimitBanned.remove(banlistItemFirst)
                    
                    # Add to dictionary for creating 'conf' file.
                    banlistCardDict[cardKonamiId] = {
                        "name": cardName,
                        "passcode": cardPasscode,
                        "konami_id": cardKonamiId,
                        "qty": qty
                    }
                    #Utils.log(f"Card info => {cardPasscode} | name: {cardName}")
        else:
            Utils.log("Banlist, Set File => JSON file parsing failed!")

    # Create conf whitelist file
    if banlistCardDict:
        # First, add manually cards that does not have passcode. Format: passcode qty name
        banlistContents += f"10000080 3 # The Winged Dragon of Ra - Sphere Mode \n"

        # Iterate over JSON items.
        for key in banlistCardDict:
            if key and key != 0 :
                cardKonamiId: int = key
                item = banlistCardDict[cardKonamiId]
                cardPasscode: int = int(item["passcode"])
                cardName: str = str(item["name"])
                qty: int = int(item["qty"])

                # Write qty to CONF file.
                if qty > 0:
                    contentToWrite: str = f"{cardPasscode} {qty} # {cardName}"
                    banlistContents += contentToWrite + "\n"
                    if qty < 3:
                        Utils.log(f"Banlist, CONF => Card is restricted to { qty } | { cardName }")
                    #Utils.log(f"Card to write => {contentToWrite}")
                else:
                    Utils.log(f"Banlist, CONF => Card is banned | { cardName }")
        # Create output file
        Utils.write_file(FILE_OUTPUT_BANLIST, banlistContents)

# Main
try:
    # Create folders
    Path(FOLDER_OUTPUT).mkdir(parents=True, exist_ok=True)

    # Clear old log files
    Utils.clear_logs()

    # Clear existing banlist output files
    dirPath = os.path.dirname(os.path.realpath(__file__))
    banlistOutputFiles = os.listdir(dirPath)
    for item in banlistOutputFiles:
        if item.endswith(EXT_OUTPUT_BANLIST) or item.endswith(".edopro"):
            outputBanlistFileItem: str = os.path.join(dirPath, item)
            if os.path.isfile(outputBanlistFileItem):
                Utils.log(f"Output file deleted (BANLIST) => {outputBanlistFileItem}")
                os.remove(outputBanlistFileItem)
    
    # Clear existing setlist with error
    Utils.write_file(FILE_OUTPUT_ERROR_SET, "")

    # Check URL
    if INPUT_URL is None or INPUT_URL == "":
        raise Exception("Invalid INPUT_URL : Blank or null.")

    # Request page and cache it, or load cached data.
    if os.path.exists(FILE_OUTPUT_BODY) and not DEBUG:
        os.remove(FILE_OUTPUT_BODY)
        Utils.log(f"Delete old file => { FILE_OUTPUT_BODY }")
    
    if not os.path.exists(FILE_OUTPUT_BODY):
        Utils.log(f"Fetching wiki data...Link => { INPUT_URL }")
        reqMain = request_page(INPUT_URL, False)
        #reqSession.close()
        if reqMain.ok:
            Utils.write_file(FILE_OUTPUT_BODY, reqMain.text)
        else:
            fileErrorText: str = FILE_OUTPUT_BODY + "_error.md"
            respContent: str = reqMain.content.decode(reqMain.encoding)
            respBody: str = reqMain.text
            if os.path.exists(fileErrorText):
                os.remove(fileErrorText)
            Utils.write_file(fileErrorText, f"# Date: { datetime.now() }\n\n# Content: \n { respContent } \n\n# Response: \n { respBody }")
            raise Exception(f"Page not downloaded, status code: {reqMain.status_code} | { reqMain.reason } | Encoding: { reqMain.encoding }")
        
    CONTENTS_HTML = Utils.read_json(FILE_OUTPUT_BODY)
    if CONTENTS_HTML is None:
        raise Exception("No valid data found!")

    # Load already done sets
    LIST_DONESET_FROMFILE = Utils.read_file(FILE_OUTPUT_DONE_SET).split()
    for doneSetItem in LIST_DONESET_FROMFILE:
        doneSetItemProper = doneSetItem.strip().upper()
        #Utils.log(f"Set '{doneSetItemProper}' is already processed.")
        LIST_DONESET.append(doneSetItemProper)

    
    Utils.log("Parsing JSON response...")
    setPrefix: str = ""
    try:
        parseData = WikiSet.fromJson(CONTENTS_HTML)
        if parseData is None:
            raise Exception ("JSON data is invalid!")
        
        count = 0
        for dataKey, dataValue in parseData.results.items():
            Utils.log(f"Set details => { dataKey } | { dataValue.fullurl }")
            
            setPrefix = ""
            setLink: str = ""
            setLinkWithCardSetList: str = ""
            setReleaseDate: datetime = None
            setReleaseDateRaw: int = 0

            # Parse release date
            try:
                setReleaseDateRaw = dataValue.printouts.release_date[0].timestamp
                setReleaseDate = datetime.fromtimestamp(setReleaseDateRaw)
            except Exception as eInner:
                setReleaseDate = None
                Utils.log_err(f"[Parse Set DateTime] Raw Value: {setReleaseDateRaw}", eInner)

            # Parse set prefix
            try:
                setLink = dataValue.fullurl.strip()
                setLinkWithCardSetList = get_setlist_from_wikilink(setLink, "OCG-AE")
                setPrefix = str(dataValue.printouts.prefix[0]).strip()
            except Exception as eInner:
                Utils.log_err(f"[Parse Set prefix]", eInner)
                    
            # Check if set is already processed or is invalid.
            if setPrefix.isspace():
                Utils.log(f"Skipped : {setLink}")
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
                        successCardList = process_setlist(dataKey, setLinkWithCardSetList, outputFileSet, outputListCardData)
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
                                Utils.append_file(FILE_OUTPUT_DONE_SET, f"{setPrefix}{NEWLINE}")
                            else:
                                Utils.log(f"Failed to parse Set list with prefix '{setPrefix}'. Check logs.")
                                #raise Exception(f"Failed to parse Set list with prefix '{setPrefix}'. Check logs.")
                        
                        outputListCardData.clear()

                    Utils.log(LINE_BREAK)
                    time.sleep(DELAY_SETLIST) # Throttle process to prevent overloading website.
            
            if count == MAX_SET_TO_PROCESS:
                break
    except Exception as innerEx:
        Utils.log_err("Parse Wiki JSON", innerEx)
        if setPrefix:
            Utils.append_file(FILE_OUTPUT_ERROR_SET, f"{setPrefix}{NEWLINE}")
        raise Exception("JSON Data cannot be parsed!")

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
