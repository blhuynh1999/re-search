from sys import argv, stderr
from flask import Flask, request, redirect, make_response, url_for
from flask import render_template
from prof import Professor
from profsDB import profsDB
from CASClient import CASClient
from updateDB import updateDB, createProf, deleteProf
from profPreferencesDB import profPreferencesDB
import psycopg2
from pathlib import Path
from datetime import datetime
from pytz import timezone
from os import remove, path
import io
from PIL import Image
import csv
from match import optimizePreferences


app = Flask(__name__, template_folder='.')

APP_ROUTE = path.dirname(path.abspath(__file__))

# Generated by os.urandom(16)
app.secret_key = b'8\x04h\x0f\x08U0\xde\x1a\x92V\xe3\xd3\x9b5\xfa'

def getProfs(search_criteria, input_arguments):
    profsDB_ = profsDB()
    error_statement = profsDB_.connect()
    profs = []
    if error_statement == '':
        connection = profsDB_.conn
        try:
            if len(input_arguments) != 0:
                profs = profsDB_.displayProfessorsByFilter(connection, search_criteria, input_arguments)
            else:
                profs = profsDB_.displayAllProfessors(connection)
            profs = profsDB_.return_profs_list(profs)
        except Exception as e:
            error_statement = str(e)
    else:
        print(error_statement)

    profsDB_.disconnect()
    return profs, error_statement

@app.route('/')
@app.route('/index')
def index():

    html = render_template('templates/index.html')
    response = make_response(html)
    return response

@app.route('/search')
def search():

    username = CASClient().authenticate()

    html = render_template('templates/profs.html', username=username)
    response = make_response(html)
    return response

@app.route('/button')
def button():

    username = CASClient().authenticate()

    html = render_template('templates/search.html')
    response = make_response(html)
    return response

@app.route('/about')
def about():

    html = render_template('templates/about.html')
    response = make_response(html)
    return response

@app.route('/searchResults', methods=['GET'])
def searchResults():   

    username = CASClient().authenticate()

    search_criteria, input_arguments = getSearchCriteria()

    profs, error_statement = getProfs(search_criteria, input_arguments)

    html = ''
    if error_statement == '':

        if len(profs) == 0:
            html += '<div class="h5 no-search-results">' + \
                        "No search results. Please try use different keywords." + \
                    '</div>'

        i = 0
        for prof in profs:
            src = prof[11]

            # display image if in database
            if prof[12] != None:
                imageBytes = bytes(prof[12])
                image = Image.open(io.BytesIO(imageBytes))

                imageExtension = prof[13]

                netID = prof[0]
                filename = netID + '.' + imageExtension
                destination = "/".join(["static/profImages/", filename])
                image.save(destination)
                src = destination

            website = ''
            email = ''
            past_papers = ''
            if prof[4] != '':
                email = '<a href="mailto:' + prof[4] + '"><img class="icon" src="static/images/email-icon.png"></a>'
            if prof[6] != '':
                website = '<a href="' + prof[6] + '" target="_blank"><img class="icon" src="static/images/website-icon.png"></a>'
            if str(prof[14]) != '':
                past_papers = '<br><a href=' + str(prof[14]) + ' target="_blank" class="previous-papers">Previous Papers Advised</a>'    


            html += '<div class="row">' + \
                        '<div class="prof-image">' + \
                            '<img src="' + src + '"/>' + \
                        '</div>' + \
                        '<div class="prof-info" onclick=' + '"collapse(' + str(i) + ')">' + \
                            '<p class="prof-name h5">' + prof[1] + ' ' + prof[2] + '</p>' + \
                            '<p class="prof-more-info">' + prof[3] + '</p>' + \
                            '<p class="prof-more-info">' + prof[8] + '</p>' + \
                            '<p class="prof-more-info">' + prof[5] + '</p>' + \
                            '<p class="prof-more-info">' + prof[7] + '</p>' + \
                            email + \
                            website + \
                        '</div>' + \
                        '<div class="add-prof-selection" onclick="addProfPreference(\'' + prof[1] + " " + prof[2] + '\')"><p>Add to advisor preferences</p></div>' + \
                        '<div class="button-div">' +\
                            '<button type="button" class="button" onclick=' + '"collapse(' + str(i) + ')"><img class="icon-button" id= img-' + str(i) + ' src="static/images/arrow_down.png"></button>' + \
                        '</div>' + \
                    '</div>' + \
                    '<div class="panel" id =panel-' + str(i) + '>' + \
                        '<div class="info-left">' + \
                            '<p class="sub-title"> Bio: </p>' + \
                            '<p class ="sub-info">' + prof[10] + '</p>' + \
                        '</div>' + \
                        '<div class="info-right">' + \
                            '<p class="sub-title"> Academic Interests: </p>' + \
                            '<p class ="sub-info">' + prof[9] + '</p>' + \
                            past_papers + \
                        '</div>' + \
                    '</div>'
            i+=1
    else:
        html = render_template('templates/profs.html', error_statement=error_statement)
        print(error_statement, file=stderr)
    response = make_response(html)
    return response

def getSearchCriteria():
    input_arguments = []

    name = request.args.get('nameNetid')
    area = request.args.get('area')

    search_criteria = ''

    # search name/netid
    if name is None:
        name = ''
    name = name.strip()
    name = name.replace('%', r'\%')
    names = name.split()

    if len(names)==1:
        search_criteria += '(first' + ' ILIKE ' + '%s' + ' OR '
        search_criteria += 'last' + ' ILIKE ' + '%s' + ' OR '
        search_criteria += 'netid' + ' ILIKE ' + '%s)' + ' AND '
        input_arguments.append('%'+names[0]+'%')
        input_arguments.append('%'+names[0]+'%')
        input_arguments.append('%'+names[0]+'%')
    elif len(names) > 1:
        search_criteria += '((first' + ' ILIKE ' + '%s' + ' OR '
        search_criteria += 'last' + ' ILIKE ' + '%s' + ') AND '
        search_criteria += '(first' + ' ILIKE ' + '%s' + ' OR '
        search_criteria += 'last' + ' ILIKE ' + '%s))' + ' AND '
        input_arguments.append('%'+names[0]+'%')
        input_arguments.append('%'+names[0]+'%')
        input_arguments.append('%'+names[1]+'%')
        input_arguments.append('%'+names[1]+'%')

    # search research area/ bio
    if area is None:
        area = ''
    area = area.strip()
    area = area.replace('%', r'\%')
    areas = area.split(",")

    if len(areas) == 1:
        search_criteria += '(area' + ' ILIKE ' + '%s' + ' OR '
        input_arguments.append('%'+areas[0]+'%')
        search_criteria += 'bio' + ' ILIKE ' + '%s)' + ' AND '
        input_arguments.append('%'+areas[0]+'%')
    else:
        for i in range(len(areas)):
            search_criteria += '(area' + ' ILIKE ' + '%s' + ' OR '
            input_arguments.append('%'+areas[i]+'%')
            search_criteria += 'bio' + ' ILIKE ' + '%s)' + ' AND '
            input_arguments.append('%'+areas[i]+'%')

    if search_criteria != '' and search_criteria != None:
        search_criteria = search_criteria[:-5]
    return search_criteria, input_arguments


#----------------------------------------------------------------------------------------------------#
# Admin
#----------------------------------------------------------------------------------------------------#


@app.route('/admin', methods=["GET"])
def admin():

    # check if user is an admin
    netID = CASClient().authenticate().rstrip('\n')

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    deniedAccess = ''

    conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE netid=%s", [netID])
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result == None:
        deniedAccess = 'deniedAccess'

    html = render_template('templates/admin.html', username=netID, deniedAccess=deniedAccess)
    response = make_response(html)
    return response


@app.route('/profinfo', methods=["GET"])
def profinfo():
    netID = request.args.get('netid')
    prof, error_statement = getProfs('netid ILIKE %s', [netID])
    html = ''

    if error_statement == '':
        if len(prof) == 0:            
            html = "<h2 class='heading' style='color: #CB2200; font-size:large'>No such professor found. Create a new professor below.</h2>" + \
                    "<div class='profForm'>" + \
                                "<form>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>NetID</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='netid' name='netid' value='" + netID + "' readonly>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>First Name</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='firstname' name='firstname' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Last Name</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='lastname' name='lastname' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Title</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='phone' name='phone' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Email</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='email' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Phone Number</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='title' name='title' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Website</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='website' name='website' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Office</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='rooms' name='rooms' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Department</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='department' name='department' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Research Interests</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<input type='text' class='form-control' id='areas' name='areas' value='""'>" + \
                                        "</div>" + \
                                    "</div>" + \
                                    "<div class='form-group row'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Bio</label>" + \
                                        "<div class='col-sm-10'>" + \
                                        "<textarea class='form-control' id='bio' name='bio' rows='5'>""</textarea>" + \
                                        "</div>" + \
                                    "</div>" + \
                            "</form>" + \
                            "<form id='upload-form' action='/upload' method='POST' enctype='multipart/form-data'>" + \
                                "<input type='file' id='file' name='file' accept='image/*'>" + \
                                "<input type='submit' value='Upload'>" + \
                            "</form>" + \
                    "</div>" + \
                    """<form method="get" id="saveForm">
                        <button type="submit" class="btn btn-primary btn btn-block" id="Save">Save</button>
                        <button type="submit" class="btn btn-secondary btn btn-block" id="Cancel">Cancel</button>
                    </form>"""      
        else:
            prof = prof[0]

            src = prof[11]
            # display image if in database
            if prof[12] != None:
                imageBytes = bytes(prof[12])
                image = Image.open(io.BytesIO(imageBytes))

                imageExtension = prof[13]

                netID = prof[0]
                filename = netID + '.' + imageExtension
                destination = "/".join(["static/profImages/", filename])
                image.save(destination)
                src = destination

            html = "<div class='profForm'>" + \
                        "<form>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>NetID</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='netid' name='netid' value='" + prof[0] + "' readonly>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>First Name</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='firstname' name='firstname' value='" + prof[1] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Last Name</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='lastname' name='lastname' value='" + prof[2] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Title</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='phone' name='phone' value='" + prof[3] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Email</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='email' value='" + prof[4] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Phone Number</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='title' name='title' value='" + prof[5] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Website</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='website' name='website' value='" + prof[6] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Office</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='rooms' name='rooms' value='" + prof[7] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Department</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='department' name='department' value='" + prof[8] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Research Interests</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<input type='text' class='form-control' id='areas' name='areas' value='" + prof[9] + "'>" + \
                                "</div>" + \
                            "</div>" + \
                            "<div class='form-group row'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Bio</label>" + \
                                "<div class='col-sm-10'>" + \
                                "<textarea class='form-control' id='bio' name='bio' rows='5'>" + prof[10] + "</textarea>" + \
                                "</div>" + \
                            "</div>" + \
                       "</form>" + \
                        "<form id='upload-form' action='/upload' method='POST' enctype='multipart/form-data'>" + \
                            "<input type='file' id='file' name='file' accept='image/*'>" + \
                            "<input type='submit' value='Upload'>" + \
                        "</form>" + \
                        "<img class='profImageDisplay' id='profImageDisplay' src='" + src + "'></img>" + \
                    "</div>" + \
                    """<form method="get" id="saveForm">
                            <button type="submit" class="btn btn-secondary btn btn-block" id="Save">Save</button>
                            <button type="submit" class="btn btn-secondary btn btn-block" id="Cancel">Cancel</button>
                            <button type="submit" class="btn btn-danger btn btn-block" id="Delete">Delete</button>
                        </form>"""
    else:
        print(error_statement, file=stderr)
    response = make_response(html)
    response.set_cookie('netid', netID)
    return response

def newProf(netid):
    prof = Professor(netid)
    prof.setTitle(request.args.get('title'))
    prof.setFirstName(request.args.get('firstname'))
    prof.setLastName(request.args.get('lastname'))
    prof.setEmail(request.args.get('email'))
    prof.setPhoneNumber(request.args.get('phone'))
    prof.setWebsite(request.args.get('website'))
    prof.setRooms(request.args.get('rooms'))
    prof.setDepartment(request.args.get('department'))
    prof.setResearchAreas(request.args.get('areas'))
    prof.setBio(request.args.get('bio'))
    imageExtension = request.args.get('image').split('.')[-1]
    imagePath = "static\profImages\\" + netid + "." + imageExtension
    prof.setImagePath(imagePath)
    return prof

@app.route('/displayprof', methods=["GET"])
def displayprof():
    netID = request.cookies.get('netid')
    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    prof = newProf(netID)
    error_statement, returned = updateDB(conn, prof)
    if returned == False:
        error_statement = createProf(conn, prof)
    conn.close()
    if error_statement != '':
        print(error_statement)

    prof_, error_statement = getProfs('netid ILIKE %s', [netID])
    prof = prof_[0]
    if error_statement == '':

        src = prof[11]

        # display image if in database
        if prof[12] != None:
            imageBytes = bytes(prof[12])
            image = Image.open(io.BytesIO(imageBytes))

            imageExtension = prof[13]

            netID = prof[0]
            filename = netID + '.' + imageExtension
            destination = "/".join(["static/profImages/", filename])
            image.save(destination)
            src = destination

        html = "<h2 class='heading'>This the updated information for " + prof[1] + " " + prof[2] + ":</h2><hr>"
        html += "<table style='text-align: left;' class='profInfoTable'> " + \
                    '<tr>' + \
                        "<td align='right' class='label'>NetID:</td>" + \
                        "<td>" + prof[0] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'></title>First Name:</td>" + \
                        "<td>" + prof[1] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'></title>Last Name:</td>" + \
                        "<td>" + prof[2] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Phone:</td>" + \
                        "<td>" + prof[5] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Email:</td>" + \
                        "<td>" + prof[4] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Title:</td>" + \
                        "<td>" + prof[3] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Website:</td>" + \
                        "<td>" + prof[6] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Rooms:</td>" + \
                        "<td>" + prof[7] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Department:</td>" + \
                        "<td>" + prof[8] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right class='label'>Areas:</td>" + \
                        "<td>" + prof[9]+   "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Bio:</td>" + \
                        "<td>" + prof[10] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td align='right' class='label'>Image File:</td>" + \
                        "<td>" + prof[11] + "</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td>" + "<img class='profImageDisplay' id='profImageDisplay' src='" + src + "'></img>" + "</td>" +\
                    "</tr>"  + \
            "</table>" + \
            """<form method="get" id="editOtherForm">
                <button type="submit" class="btn btn-secondary btn-lg">Edit Another Professor</button>
            </form>"""
    else:
        print(error_statement, file=stderr)

    response = make_response(html)
    return response

@app.route('/deleteprof', methods=["GET"])
def deleteprof():
    netID = request.args.get('netid')

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    error_statement = deleteProf(conn, netID)
    conn.close()
    if error_statement != '':
        print(error_statement)

    html = ''
    response = make_response(html)
    return response

@app.route('/profPreferences', methods=["GET"])
def profPreferences():
    first = request.args.get('first')
    if first == "":
        first = None
        print('hello', first)
    second = request.args.get('second')
    third = request.args.get('third')
    fourth = request.args.get('fourth')

    profsDB_ = profsDB()
    error_statement = profsDB_.connect()
    profs = []
    if error_statement == '':
        connection = profsDB_.conn
        try:
            profs = profsDB_.displayAllProfessors(connection)
            profs = profsDB_.return_profs_list(profs)
        except Exception as e:
            error_statement = str(e)
            print(error_statement)

    profsDB_.disconnect()

    html = render_template('templates/profPreferences.html', 
        first=first, second=second, third=third, fourth=fourth,
        profs=profs)
    response = make_response(html)
    return response

@app.route('/submitPreferences', methods=["GET"])
def submitPreferences():

    username = CASClient().authenticate().rstrip('\n')

    advisor1 = request.args.get('Advisor1')
    print('hello', advisor1)
    if advisor1 == None:
        advisor1 = ''
    advisor2 = request.args.get('Advisor2')
    if advisor2 == None:
        advisor2 = ''
    advisor3 = request.args.get('Advisor3')
    if advisor3 == None:
        advisor3 = ''
    advisor4 = request.args.get('Advisor4')
    if advisor4 == None:
        advisor4 = ''

    advisor1Comments = request.args.get('Advisor1Comments')
    if advisor1Comments == None:
        advisor1Comments = ''
    advisor2Comments = request.args.get('Advisor2Comments')
    if advisor2Comments == None:
        advisor2Comments = ''
    advisor3Comments = request.args.get('Advisor3Comments')
    if advisor3Comments == None:
        advisor3Comments = ''
    advisor4Comments = request.args.get('Advisor4Comments')
    if advisor4Comments == None:
        advisor4Comments = ''

    courseSelection = request.args.get('courseSelection')

    fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    eastern = timezone('America/New_York')
    loc_dt = datetime.now(eastern)
    submittedTime = loc_dt.strftime(fmt)
    if submittedTime == None:
        submittedTime = ''

    completedTime = submittedTime

    # insert data into 'preferences database'
    profPrefDB = profPreferencesDB()
    error_statement = profPrefDB.connect()
    if error_statement == '' :
        report = profPrefDB.createProfPreference([username, courseSelection,
            advisor1, advisor1Comments, advisor2, advisor2Comments, advisor3, 
            advisor3Comments, advisor4, advisor4Comments, submittedTime, completedTime])
    else:
        print(error_statement, file=stderr)

    profPrefDB.disconnect()

    response = make_response(report)
    return response

@app.route('/getPreferences', methods=["GET"])
def getPreferences():

    # username = CASClient().authenticate().rstrip('\n')

    profPrefDB = profPreferencesDB()
    error_statement = profPrefDB.connect()

    report_preferences = []
    if error_statement == '' :
        report_preferences = profPrefDB.getProfPreference()
        report = report_preferences[0]
        preferences = report_preferences[1:]

        if report == "Failed Download":
            print(report, file=stderr)
        else:
            print(report)
    else:
        print(error_statement, file=stderr)
    
    profPrefDB.disconnect()

    html = ''

    header = ["Serial","SID","Submitted Time","Completed Time","Modified Time","Draft","UID","Username","Course Selection","First Advisor Choice","Topic or Comments","Second Advisor Choice","Topic or Comments","Third Advisor Choice","Topic or Comments","Fourth Advisor Choice","Topic or Comments"]
    # spacing = [""] * 17
    with open('preferences.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(header)
        # csv_writer.writerow(spacing)
        for row in preferences:
            csv_writer.writerow(list(row))

    with open('preferences.csv', 'r', newline='') as csv_file:
        for row in csv_file:
            html += row

    remove('preferences.csv')

    response = make_response(html)
    return response

@app.route('/getMatches', methods=["GET"])
def getMatches():

    # username = CASClient().authenticate().rstrip('\n')

    student_cap = 5
    pref_limit = 4
    report, prof_student_list, student_prof_list = optimizePreferences(student_cap, pref_limit)

    html = ''

    header = ["Professor"]
    for i in range(1, student_cap + 1):
        header.append("Student" + str(i))
    # spacing = [""] * 2
    with open('matches.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(["Student netids with an * indicate a non-ORFE advisor preference (see preferences.csv)"])
        csv_writer.writerow(header)
        # csv_writer.writerow(spacing)
        for prof in prof_student_list:
            prof_students = [prof]
            for student in prof_student_list[prof]:
                prof_students.append(student)
            csv_writer.writerow(prof_students)

    with open('matches.csv', 'r', newline='') as csv_file:
        for row in csv_file:
            html += row

    remove('matches.csv')

    response = make_response(html)
    return response

@app.route('/upload', methods=["POST"])
def upload():
    target = path.join(APP_ROUTE, 'static/profImages')
    netID = request.cookies.get('netid')
    
    file = request.files.getlist("file")[0]
    fileExtension = file.filename.split('.')[-1]
    file_data = file.read()
    id_item = 254
    SaveImageToDatabase(netID, id_item, file_data, fileExtension)
    return ('', 204)

def SaveImageToDatabase(netID, id_item, FileImage, fileExtension):

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    error_statement = ''

    stmt = ""
    stmt += "UPDATE profs"
    stmt += " set image_actual=%s,"
    stmt += " image_extension=%s"
    stmt += " WHERE netid=%s"

    try:
        conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = conn.cursor()
        cur.execute(stmt, [FileImage, fileExtension, netID])
        conn.commit()
        cur.close()
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        error_statement = str(error)
        print(error_statement)
    finally:
        if conn is not None:
            conn.close()
        return error_statement

@app.route('/getAdmins', methods=["GET"])
def getAdmins():
    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    deniedAccess = ''

    conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    cur = conn.cursor()
    cur.execute("SELECT netid FROM admins")
    row = cur.fetchone()
    admins = ""
    while row is not None:
        admins += str(row[0]) + ","
        row = cur.fetchone()
    admins = admins[:-1]
    cur.close()
    conn.close()
    return admins

@app.route('/addNewAdmin', methods=["GET"])
def addNewAdmin():
    netid = request.args.get('netid')

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    error_statement = ''

    try:
        conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = conn.cursor()
        stmt = "INSERT INTO admins(netid) VALUES(%s)"
        cur.execute(stmt, [netid])
        conn.commit()
        cur.close()
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        error_statement = str(error)
        print(error_statement)
    finally:
        if conn is not None:
            conn.close()
        return error_statement


@app.route('/removeAdmin', methods=["GET"])
def removeAdmin():
    netid = request.args.get('netid')

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    error_statement = ''
    try:
        conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = conn.cursor()
        stmt = "DELETE FROM admins WHERE netid=%s"

        cur.execute(stmt, [netid])
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        error_statement = str(error)
        print(error_statement)
    finally:
        if conn is not None:
            conn.close()
        return error_statement



if __name__ == '__main__':
    
    if (len(argv) != 2):
        print('Usage: ' + argv[0] + ' port', file=stderr)
        exit(1)

    try:
        port = int(argv[1])
    except:
        print("Port must be an integer", file=stderr)
        exit(1) 

    app.run(host='0.0.0.0', port=int(argv[1]), debug=True)
    app.run()
