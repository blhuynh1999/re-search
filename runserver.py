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


app = Flask(__name__, template_folder='.')

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
    return profs, error_statement

@app.route('/')
@app.route('/index')
def index():

    html = render_template('templates/index.html')
    response = make_response(html)
    return response

@app.route('/search')
def search():

    # username = CASClient().authenticate()

    html = render_template('templates/profs.html')
    response = make_response(html)
    return response

@app.route('/logout', methods=['GET'])
def logout():
    
    # casClient = CASClient()
    # casClient.authenticate()
    # casClient.logout()

    html = render_template('templates/index.html')
    response = make_response(html)
    return response

@app.route('/button')
def button():

    # username = CASClient().authenticate()

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

    # username = CASClient().authenticate()

    search_criteria, input_arguments = getSearchCriteria()

    profs, error_statement = getProfs(search_criteria, input_arguments)

    html = ''
    if error_statement == '':

        if len(profs) == 0:
            html += '<div class="no-search-results">' + \
                        "<h2>No search results. Please try use different keywords.</h2>" + \
                    '</div>'

        i = 0
        for prof in profs:
            src = prof[11]
            website = ''
            email = ''
            if prof[4] != '':
                email = '<a href="mailto:' + prof[4] + '"><img class="icon" src="static/images/email-icon.png"></a>'
            if prof[6] != '':
                website = '<a href="' + prof[6] + '"><img class="icon" src="static/images/website-icon.png"></a>'

            html += '<div class="row">' + \
                        '<div class="prof-image">' + \
                            '<img src="' + src + '"/>' + \
                        '</div>' + \
                        '<div class="prof-info" onclick=' + '"collapse(' + str(i) + ')">' + \
                            '<p class="prof-name">' + prof[1] + ' ' + prof[2] + '</p>' + \
                            '<p class="prof-more-info">' + prof[3] + '</p>' + \
                            '<p class="prof-more-info">' + prof[8] + '</p>' + \
                            '<p class="prof-more-info">' + prof[5] + '</p>' + \
                            '<p class="prof-more-info">' + prof[7] + '</p>' + \
                            email + \
                            website + \
                        '</div>' + \
                        '<div class="add-prof-selection" onclick="addProfPreference(\'' + prof[1] + " " + prof[2] + '\')"><p>Add professor</p></div>' + \
                        '<div class="button-div">' +\
                            '<button type="button" class="button" onclick=' + '"collapse(' + str(i) + ')"><img class="icon-button" id= img-' + str(i) + ' src="static/images/plus.png"></button>' + \
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
    return profs, error_statement


#----------------------------------------------------------------------------------------------------#
# Admin
#----------------------------------------------------------------------------------------------------#


@app.route('/admin', methods=["GET"])
def admin():
    html = render_template('templates/admin.html')
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
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Lat Name</label>" + \
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
                                    "<div class='input-group mb-3'>" + \
                                        "<label for='colFormLabel' class='col-sm-2 col-form-label'>Image</label>" + \
                                        "<div class='custom-file'>" + \
                                            "<input type='file' class='custom-file-input' id='myfile' name='myfile'>" + \
                                            "<label class='custom-file-label' for='inputGroupFile02' aria-describedby='inputGroupFileAddon02'>" + \
                                            "</label>" + \
                                        "</div>" + \
                                        "<div class='input-group-append'>" + \
                                            "<span class='input-group-text' id='inputGroupFileAddon02'>Upload</span>" + \
                                        "</div>" + \
                                    "</div>" + \
                            "</form>" + \
                            "</div>" + \
                            """<form method="get" id="saveForm">
                                    <input class="searchButton overwriteButton" type="submit" id="Save" value="Save">
                                    <input class="searchButton cancelOverwriteButton" type="submit" id ="Cancel" value="Cancel">
                                    <input class="searchButton deleteButton" type="submit" id ="Delete" value="Delete">
                                </form>"""        
        else:
            prof = prof[0]
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
                            "<div class='input-group mb-3'>" + \
                                "<label for='colFormLabel' class='col-sm-2 col-form-label'>Image</label>" + \
                                "<div class='custom-file'>" + \
                                    "<input type='file' class='custom-file-input' id='myfile' name='myfile'>" + \
                                    "<label class='custom-file-label' for='inputGroupFile02' aria-describedby='inputGroupFileAddon02'>" + \
                                    prof[11] +\
                                    "</label>" + \
                                "</div>" + \
                                "<div class='input-group-append'>" + \
                                    "<span class='input-group-text' id='inputGroupFileAddon02'>Upload</span>" + \
                                "</div>" + \
                            "</div>" + \
                       "</form>" + \
                    "</div>" + \
                    """<form method="get" id="saveForm">
                            <input class="searchButton overwriteButton" type="submit" id="Save" value="Save">
                            <input class="searchButton cancelOverwriteButton" type="submit" id ="Cancel" value="Cancel">
                            <input class="searchButton deleteButton" type="submit" id ="Delete" value="Delete">

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
    imagePath = "static\profImages\\" + netid + ".jpg"
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
    print(returned)
    if returned == False:
        error_statement = createProf(conn, prof)
    conn.close()
    if error_statement != '':
        print(error_statement)

    prof_, error_statement = getProfs('netid ILIKE %s', [netID])
    prof = prof_[0]
    if error_statement == '':
        html = "<h2 class='heading'>This the updated infomation for " + prof[1] + " " + prof[2] + ":</h2><hr>"
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
                        "<td>""</td>" + \
                    "</tr>" + \
                    "<tr>" + \
                        "<td></td>" + \
                    "</tr>"  + \
            "</table>" + \
            """<form method="get" id="editOtherForm"><input class="searchButton cancelOverwriteButton" type="submit" value="Edit Another Professor"></form>"""
    else:
        print(error_statement, file=stderr)

    response = make_response(html)
    return response

@app.route('/deleteprof', methods=["GET"])
def deleteprof():
    netID = request.cookies.get('netid')

    hostname = 'ec2-52-200-119-0.compute-1.amazonaws.com'
    username = 'hmqcdnegecbdgo'
    password = 'c51235a04a7593a9ec0c13821f495f259a68d2e1ab66a93df947ab2f31970009'
    database = 'd99tniu8rpcj0o'

    conn = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    error_statement = deleteProf(conn, netID)
    conn.close()
    if error_statement != '':
        print(error_statement)

    html = render_template('admin.html')
    response = make_response(html)
    return response

@app.route('/profPreferences', methods=["GET"])
def profPreferences():
    first = request.args.get('first')
    if first == "":
        first = ""
    second = request.args.get('second')
    if first == "":
        first = ""
    third = request.args.get('third')
    if first == "":
        first = ""
    fourth = request.args.get('fourth')
    if first == "":
        first = ""

    html = render_template('templates/profPreferences.html', 
        first=first, second=second, third=third, fourth=fourth)
    response = make_response(html)
    return response

@app.route('/submitPreferences', methods=["GET"])
def submitPreferences():

    username = CASClient().authenticate().rstrip('\n')

    advisor1 = request.args.get('Advisor1')
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
    if courseSelection == None:
        courseSelection = ''

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
        profPrefDB.createProfPreference([username, courseSelection,
            advisor1, advisor1Comments, advisor2, advisor2Comments, advisor3, 
            advisor3Comments, advisor4, advisor4Comments, submittedTime, completedTime])
        profPrefDB.disconnect()
    else:
        print(error_statement, file=stderr)

    response = make_response(error_statement)
    return response


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
