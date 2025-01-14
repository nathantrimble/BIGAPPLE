from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
#from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template, Markup
from bson.objectid import ObjectId

import pprint
import os
import pymongo
import sys



app = Flask(__name__)

app.debug = False #Change this to False for production
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging



app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#mongo connections
connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]
client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['nycstateofmind']
#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)


#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    return render_template('home.html')

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    alertm = Markup('<div class="alert alert-info">You were logged out</div>')
    return render_template('home.html', am = alertm)

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    alertm = ''
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)
        alertm = Markup('<div class="alert alert-danger">'+ message +'</div>')
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            message='You were successfully logged in as ' + session['user_data']['login'] + '.'
            alertm = Markup('<div class="alert alert-success">'+ message +'</div>')
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
            alertm = Markup('<div class="alert alert-info">'+ message + '</div>')
    return render_template('home.html', am=alertm)


@app.route('/forumpage', methods=['GET','POST'])
def renderPage1():
    if request.method == 'POST' and 'github_token' in session:
        postcontent= request.form['message']
        newdoc = {"Content" : postcontent , "Author":  session['user_data']['login'], "Likes" : 0 , "Dislikes" : 0 }
        collection.insert_one(newdoc)
    elif  request.method == 'POST' and 'github_token' not in session:
        return redirect('/')

    postlist = ""
    for docs in collection.find():
        pc = docs['Content']
        pa = docs['Author']
        plikes = str(docs['Likes'])
        pdislikes = str(docs['Dislikes'])
        pid = str(docs["_id"])
        postlist += Markup('<div class="card"> <div class="card-body"> <h4 class="card-title">' + pc + '</h4> <p class="card-text">' + pa + '</p>    <form action="/forumpaged" method="POST"><input type="submit" value=' + pid +' class="btn btn-outline-success" name="ObjectID" id="likeb"><label for="likeb">Like: '+ plikes +'</label></form>  <form action="/forumpaged" method="POST"><input type="submit" value=' + pid +' class="btn btn-outline-danger" name="ObjectID" id="dislikeb"><label for="dislikeb">Dislike: '+ pdislikes +'</label></form> </div></div>')
    return render_template('forumpage.html', pl = postlist)

@app.route('/forumpaged', methods=['GET','POST'])
def updateLD():
    print(request)
    buttonname = request.form['ObjectID']
    query = {"_id" : buttonname}
    changes = {'$set':{'Dislikes':5}}
    collection.update_one(query,changes)
    postlist = ""
    for docs in collection.find():
        pc = docs['Content']
        pa = docs['Author']
        plikes = str(docs['Likes'])
        pdislikes = str(docs['Dislikes'])
        pid = str(docs["_id"])
        postlist += Markup('<div class="card"> <div class="card-body"> <h4 class="card-title">' + pc + '</h4> <p class="card-text">' + pa + '</p>   <form action="/forumpaged" method="POST"><input type="submit" value=' + pid +' class="btn btn-outline-sucess" name="ObjectID" id="likeb"><label for="likeb">Like: '+ plikes +'</label></form>  <form action="/forumpaged" method="POST"><input type="submit" value=' + pid +' class="btn btn-outline-danger" name="ObjectID" id="dislikeb"><label for="dislikeb">Dislike: '+ pdislikes +'</label></form> </div></div>')
    return render_template('forumpage.html', pl = postlist)

@app.route('/about')
def renderAboutPage():
    return render_template('about.html')

@app.route('/googleb4c3aeedcc2dd103.html')
def render_google_verification():
    return render_template('googleb4c3aeedcc2dd103.html')

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run()
