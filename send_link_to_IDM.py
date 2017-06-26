'''
Send links from file.txt to IDM
file.txt content: http://link * filename(' * ' as delimiter)
'''
# http://www.internetdownloadmanager.com/support/idm_api.html
# interface ICIDMLinkTransmitter2 : ICIDMLinkTransmitter
# {
#    HRESULT SendLinkToIDM2(BSTR bstrUrl, BSTR bstrReferer, BSTR bstrCookies, BSTR bstrData,
#             BSTR bstrUser, BSTR bstrPassword, BSTR bstrLocalPath, 
#             BSTR bstrLocalFileName, long lFlags, VARIANT reserved1, VARIANT reserved2);
#     /*Transfers one link (URL) to IDM, brings Start Download dialog, or just adds the file 
#     to IDM download queue if a special flag is set.*/


#    HRESULT SendLinksArray(BSTR location, VARIANT * pLinksArray);
#     /* Transfers to IDM an array of internet links (URLs). Note that the use of this
#     function will bring "Download All Links with IDM" dialog to give user an opportunity
#     to review URLs before downloading.*/
# };
 
# Parameters of SendLinkToIDM2 function:
# bstrUrl - Url to download
# bstrReferer - Referer
# bstrCookies - cookies
# bstrData - PostData (if using POST method)
# bstrUser - UserName (if server requires authentication)
# bstrPassword - Password
# bstrLocalPath - LocalPath (where to save a file on your computer)
# bstrLocalFileName - LocalFileName (file name to save with)
# lFlags - Flags, can be zero or a combination of the following values: 
#     1 - do not show any confirmations dialogs; 
#     2 - add to queue only, do not start downloading.
# reserved1 - can be used to set a specific user-agent header with the following way:
#     reserved1.vt = VT_BSTR; reserved1.bstrVal = pbstrUA; if you don't need to specify a 
#     user agent, then reserved1.vt should be set to VT_EMPTY;
# reserved2 - not used, you should set reserved2.vt to VT_EMPTY;
 
# Paramerets of SendLinksArray function:
# Location - the referrer of download, it's assumed that the referrer is a single one 
#     for the entire array of internet links.
# pLinksArray - a pointer to 2 dimensional SAFEARRAY array of BSTR strings. 
#     For example, for N number of links, the size of the array will be (4 * N). 
#     For i changing from 0 to N-1
#     a[i,0] elements of the array are URLs to download, 
#     a[i,1] are cookies for corresponding a[i,0] URLs,
#     a[i,2] are link descriptions for corresponding URLs, 
#     a[0,3] is the user agent, all others elements a[i,3] are not used and should be always NULL.

import argparse
import comtypes.client as cc
import comtypes
import io
import os


def send_link_to_idm(link, file_name=None):
    bstrUrl = link
    bstrReferer = ""
    bstrCookies = ""
    bstrData = ""
    bstrUser = ""
    bstrPassword = ""
    bstrLocalPath = ""
    bstrLocalFileName = "" if file_name is None else file_name
    lFlags = 3
    reserved1 = comtypes.automation.VARIANT(0)
    reserved2 = comtypes.automation.VARIANT(0)
 
    idm_tlb_path = "C:\\Program Files (x86)\\Internet Download Manager\\idmantypeinfo.tlb"
    if not os.path.exists(idm_tlb_path):
        idm_tlb_path = "C:\\Program Files\\Internet Download Manager\\idmantypeinfo.tlb"
    # cc.GetModule("C:\\Program Files (x86)\\Internet Download Manager\\idmantypeinfo.tlb")
    cc.GetModule(idm_tlb_path)
    # not sure about the syntax here, but cc.GetModule will tell you the name of the wrapper it generated
    import comtypes.gen.IDManLib as IDMan
    idm1 = cc.CreateObject("IDMan.CIDMLinkTransmitter", None, None, IDMan.ICIDMLinkTransmitter2)
 
    idm1.SendLinkToIDM2(bstrUrl, bstrReferer, bstrCookies, bstrData, bstrUser,
                        bstrPassword, bstrLocalPath, bstrLocalFileName, lFlags,
                        reserved1, reserved2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='txt file that contains links to download')
    args = parser.parse_args()
    
    with io.open(args.filename, encoding='utf8') as f:
        for line in f:
            link, filename = line.strip().split(' * ') # custom delimiter here
            send_link_to_idm(link, filename)
    
if __name__ == "__main__":
    main()