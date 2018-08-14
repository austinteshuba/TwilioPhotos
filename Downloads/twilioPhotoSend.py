from firebase import firebase
from flask import Flask, request
from twilio import twiml
from twilio.rest import TwilioRestClient
from time import localtime
import cognitive_face as CF # this is the microsoft azure things
import httplib, urllib, base64, json
import requests
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse
import http.client, urllib, base64

now = localtime()
twilNum = '+12264003702'
app = Flask(__name__)

KEY = 'ff14fed082ef4105982dbd0d312f2513'  # Replace with a valid Subscription Key here.
CF.Key.set(KEY)

BASE_URL = 'https://westcentralus.api.cognitive.microsoft.com/face/v1.0'  # Replace with your regional Base URL
CF.BaseUrl.set(BASE_URL)

firebase = firebase.FirebaseApplication('https://faces-dc392.firebaseio.com/', None)

#url = "https://mhacks.intrepidcs.com"

"""
logged = False #are you logged in
admin = False
"""

#twilio code
@app.route('/', methods=["POST"])
def main():
    global firebase
    #return 'hey'
    #put the face id into firebase. if there was a body, assume it was the name and pass that in as well.
    now = localtime()
    
    #global logged
    #sending announcments
    number = request.form['From']#get the number it was sent from
    number = phoneNumberParse(number, 0)
   
    messageBody = request.form["Body"]#get the body of the message
    numberOfMedia = int(request.form["NumMedia"])

    if len(messageBody)!=0:
        if "coming" not in messageBody.lower() and "new" in messageBody.lower():#new, name: "name", etc.
            #return twiml.Response().message("hey")
            print("hey")
            body = messageBody.split("\n") # make sure that the key value pairs are seperated by spaces and new line characters
            #urlList = ''
            groupID = "family" #later, adjust this to be the phone number of the twilio user.
            person = createPerson(body, groupID)# the body is formatted as: new, name: name, and then any other data in key value pair
            #return "sure"
            for x in range (numberOfMedia):
                s = "MediaUrl" + str(x)
                img_url=request.form[s]
                
                result = faceDetect(img_url)#result gets how many faces detected.
                if len(result)==1:
                    #do stuff
                    #create a person
                    addToPerson(groupID, person, img_url)
                    print("got here")
                else:
                    print("skipped as the photo was low quality. Please be alone in these photos")
                #firebase.put("/"+ str(result), "Image", img_url)
                #make this init the person groups and train and all that
            train("family")
            result = "Thank you %s"%(str(body[1].split(":")[1]))
            print(result)
            
        else:
            #init the coming thing. so like open doors, open liftgate, start engine? ONLY if it matches with the driver's face
            if numberOfMedia==0:
                result = "do better please"
            else:
                result = coming(request.form["MediaUrl0"])
    else:
        if numberOfMedia==0:
            result = "Send something useful please."
        else:
            #confirm and identify from the database.
            name = identifyPeople(request.form["MediaUrl0"])
            #result = str(name + " " + str(certainty))
            result = str(name)
        
        

    t = MessagingResponse()
    t.message(result)
    return str(t)

def identifyPeople(imageURL, groupID = "family"):
    #take in an image id and return a list of people. currently only does one person at a time and assumes family group. 
    faceIDs = faceDetect(imageURL)#2d array
    #return(str(faceIDs))
    #return("made it!")
    #return (faceID, "0.5")
    peopleInPic = faceIdentify(([x[0] for x in faceIDs]), groupID)
    name = getPerson(peopleInPic, groupID)
    #certainty = peopleInPic[1]
    if len(name)!=0:
        return str(name)
    else:
        return "I don't know you!"

def faceIdentify(faceID, groupID):####CHECK
    url = "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/identify"
    data={}
    data["personGroupId"] = groupID
    data["faceIds"] = faceID
    json_data = json.dumps(data)
    #payload = "\r\n{\"personGroupId\":\"%s\",\r\n    \"faceIds\":[\"2d5207e8-d3c9-472c-95e5-72263763864d\", \"5f2f3322-ca3a-481d-a5c8-8822f5b85aad\"]}"%(groupID)
    headers = {
        'ocp-apim-subscription-key': "e6120b58c6a14b699d631d027da38e56",
        'content-type': "application/json",
        'cache-control': "no-cache",
        'postman-token': "38784f0b-0468-6d26-223d-8c994905ff3a"
        }

    response = requests.request("POST", url, data=json_data, headers=headers)

    print(response.json())
    peopleInPic=[]
    for x in range(len(response.json())):
        x-=1
        if dict(response.json()[x])['candidates'] != []:
            #print(x)
            formattedResponse = dict(response.json()[x])
            #print(formattedResponse)
            peopleInPic.append([str(formattedResponse['candidates'][x]['personId']), str(formattedResponse['candidates'][x]['confidence'])])
            print(peopleInPic)
    return peopleInPic

def createPerson(body, groupID, c=0):
    #takes in the split up body
    name = body[1].split(":")[1]
    #TAKE IN DATA HERE AND UPLOAD IT AS INIT
    url = "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/persongroups/%s/persons"%(groupID)

    data={}
    #data["personGroupId"] = groupID
    params = {}
    params["personGroupId"] = groupID
    param = json.dumps(params)
    data["name"] = name
    userDataString = ""
    for x in range(2, len(body)):
        userDataString+=body[x]
    data["userData"] =userDataString
    ###data["userData"] = "" include in JSON format
    json_data = json.dumps(data)
    #payload = "\r\n{ \"personGroupId\":\"%s\",\r\n    \"name\" : \"%s\"\r\n}"%(
    headers = {
        'Ocp-Apim-Subscription-Key': 'e6120b58c6a14b699d631d027da38e56',   
        }
    connt = httplib.HTTPSConnection('westcentralus.api.cognitive.microsoft.com')
    connt.request("POST", "/face/v1.0/persongroups/%s/persons?" %(groupID), json_data, headers)
    #response = requests.post(url, params = param, headers=headers, data=json_data)
    res = connt.getresponse()
    if res.status==404 and c !=1:
        u = 'https://westcentralus.api.cognitive.microsoft.com/face/v1.0/persongroups/%s'%(groupID)
        par={}
        par['personGroupId'] = groupID
        para = json.dumps(par)
        dat={}
        dat['name'] = groupID
        d = json.dumps(dat)
        #r = requests.put(url , params = para, headers=headers, data=d)
        conn = http.client.HTTPSConnection('westcentralus.api.cognitive.microsoft.com')
        conn.request("PUT", "/face/v1.0/persongroups/%s?" % (groupID), d, headers)
        print(conn.getresponse().read())
        print("Hey")
        createPerson(body, groupID, 1)
    
    
    return dict(json.loads(res.read().decode('utf-8')))["personId"]
    #print(response.text)#you can pass in user data here too!

def addToPerson(groupID, personID, imageURL):
    url = "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/persongroups/%s/persons/%s/persistedFaces"%(groupID, personID)

    payload = "\r\n{ \r\n\t\"url\" : \"%s\"\r\n}"%(imageURL)
    headers = {
        'ocp-apim-subscription-key': "e6120b58c6a14b699d631d027da38e56",
        'content-type': "application/json",
        'cache-control': "no-cache",
        'postman-token': "cac5fd63-cf1a-c96e-b54e-07402f8f5d8c"
        }

    response = requests.request("POST", url, data=payload, headers=headers)
    
def train(groupID):
    url = "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/persongroups/%s/train"%(groupID)

    headers = {
        'ocp-apim-subscription-key': "e6120b58c6a14b699d631d027da38e56",
        'content-type': "application/json",
        'cache-control': "no-cache",
        'postman-token': "83357725-d431-4271-3251-8453c8febf67"
        }

    response = requests.request("POST", url, headers=headers)
    print(response)

def getPerson(personIDs, groupID):
    names=[]
    persons = personIDs
    for personID in persons:
        print(personID)
        url = "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/persongroups/%s/persons/%s"%(groupID, personID[0])

        headers = {
            'ocp-apim-subscription-key': "e6120b58c6a14b699d631d027da38e56",
            'cache-control': "no-cache",
            'postman-token': "308f777b-2918-d49b-d8a3-8ab24de8eefa"
            }

        response = requests.request("GET", url, headers=headers)

        resp = dict(json.loads(response.text))
        #print(resp)
        personID[0] = str(resp['name'])
        personID.append(resp["userData"])#you can get user data here
    return persons



    
def faceDetect(imageURL):
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': KEY,
    }

    params = urllib.urlencode({
        # Request parameters
        'returnFaceId': 'true',
        'returnFaceLandmarks': 'false',
    })

    try:
        e = {}
        e["url"] = imageURL
        t = json.dumps(e)
        conn = http.client.HTTPSConnection('westcentralus.api.cognitive.microsoft.com')
        conn.request("POST", "/face/v1.0/detect?%s" % params, t, headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        faceIds=[]
        for x in json.loads(data.decode('utf-8')):
            print(x)
            faceIds.append([str(x["faceId"]), dict(x["faceRectangle"])])
        conn.close()
        return faceIds
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))
        #print(json.loads(response.text))
    
    print(faceIds)
    return faceIds

def coming(imageURL, groupID="family"):
    faceIDs = faceDetect(imageURL)
    if len(faceIDs)!=1:
        return("Please try another photo. Ensure you are alone.")
    peopleInPic = faceIdentify(([x[0] for x in faceIDs]), groupID)
    name = getPerson(peopleInPic, groupID)
    
    return("Ghank you %s. Your alarm is disarmed.")%(name[0][0])


def phoneNumberParse(body, phoneIndex):
    phoneNumber = body[phoneIndex:].strip()
    if len(phoneNumber) == 11 and phoneNumber[0] == "1":
        phoneNumber = phoneNumber[1:]
    elif len(phoneNumber) == 12 and phoneNumber[0:2] == "+1":
        phoneNumber = phoneNumber[2:]
    elif len(phoneNumber) > 10 or len(phoneNumber) < 10:
        phoneNumber = None
    return phoneNumber
###########################################################################

if __name__ == "__main__":
    app.run(debug = True)
