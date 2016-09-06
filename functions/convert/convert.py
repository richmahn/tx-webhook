#!/usr/bin/env python
########################################################################
# 
# NAME convert.py  -  gogs client for tx
#
# USAGE  normally called from lambda function in main.py
#     local debug
#        convert.py awsid preConvertBucket test_notification_message_file   
#                   < test_notification_message_file
#     apex build/test
#         make obs|ta|usfm   # for ajax deploy
#         from local git repo push document to git.door43.org 
#           where remote repo has webhook like 
#               bspidel/gaj-x-ymnk_obs_text_obs 
#                       en-ta-intro
#                       nw_luk_text_ulb
#     tavis
#         push code to repo tx-webhook for travis deploy
#
# DESCRIPTION perform the following on behalf of gogs webhook
#   + extract repo infor from post message
#   + curl file to tmp directory
#   + unzip file with tar
#   + determine operation to perform
#     call correct builder
#     call correct formatter
#   + send to s3
#
########################################################################

from __future__ import print_function # advanced python feature

# get required code
import os
import sys
import json
import logging
import time
import subprocess
import boto3
import requests
import tempfile

from shutil                    import copyfile
from glob                      import glob
from boto3.session             import Session
from os.path                   import join, getsize
from subprocess                import Popen, STDOUT, PIPE
from datetime                  import date
from logging.handlers          import RotatingFileHandler
from general_tools.file_utils  import unzip, add_file_to_zip, load_json_object, make_dir, write_file
from general_tools.url_utils   import join_url_parts, download_file


def ifCopy( frm, too ):
  # copy frm to too if frm exists

    if os.path.exists( frm ):
       copyFile( frm, too )

def flatten( dir, mfd ):
  # pull chunks up to chapter level
  # dir is like: /tmp/input/<user>/<repo>/
  # content is under dir [<chapter>]<chunk>.[md|txt]
    myLog( 'info', "flatten: " + dir + " mfd: " + mfd )
    os.chdir( dir )
    content =  os.path.join( dir, "content" )

    if os.path.exists( content ):
        os.chdir( content )

    mdFiles = glob( '*/*.md' ) 
    make_dir( mfd )
    print( "mdFiles" )
    print( mdFiles )
    fileCount = 0

    for mdFile in mdFiles:
        newFile = mdFile.replace( '/', '-' )
        os.rename( mdFile, os.path.join( mfd,newFile ))
        myLog( "debug", "mdFile: " + mdFile + " newFile: " + newFile )
        fileCount += 1

    myLog( "info", "mdFiles: " + str( fileCount ) )
  # want front matter to be before 01.md and back matter to be after 50.md
    ifCopy( os.path.join( dir, '_front', 'front-matter.md' ), 
            os.path.join( mfd, '00_front-matter.md' ))
    ifCopy( os.path.join( dir, '_back',  'back-matter.md'  ), 
            os.path.join( mfd, '51_back-matter.md' ))

def mv_md( dir ):
  # change txt files from dir to have .md extensions
    myLog( 'info', "mv_md dir: " + dir )
    
    for root, dirs, files in os.walk( dir ):
        myLog( "detail", "root: " + root )
        c = 1

        if debugLevel > 5:
           for nme in files:
               srcPath =  join( root, nme )
               myLog( "debug", "srcPath: " + srcPath  )

        for nme in files:
            srcPath =  join( root, nme )
            myLog( "details", "srcPath: " + srcPath  )  

            if srcPath.find( ".txt" ) > -1:
                dst = srcPath[ :srcPath.rfind( '.' ) ]
                myLog( "debug", "dst:     " + dst + '.md' )
                os.rename( srcPath, dst + '.md' )

        if debugLevel > 5:
           for nme in files:
               srcPath =  join( root, nme )
               myLog( "debug", "srcPath: " + srcPath  )


debugLevel = 6

def myLog( level, msg): # very simple local debug 
    sw = {
      "debug"   : 6,
      "loops"   : 5,
      "detail"  : 4,
      "info"    : 3,
      "warning" : 2,
      "error"   : 1
    }

    l = sw.get( level, 5 )

    if l <= debugLevel:
        print( ( "  " * l ) + level + " " + " " * ( 7 - len( level )) + msg )

if debugLevel == 5:
  print( "environ: " )
  print( os.environ ) 

ACCESS_KEY = os.environ[ 'AWS_ACCESS_KEY_ID' ]
SECRET_KEY = os.environ[ 'AWS_SECRET_ACCESS_KEY' ]
MAXJSON    = 10000
AWS_REGION = "us-east-1"
#AWS_REGION = "Oregon"

# define file paths
workDir  = '/tmp/'
inDir    = workDir  + 'input/'
outDir   = workDir  + 'output/'
#bucket   = 'test-door43.org' # pusher repo hash fmt
#config   = './.s3-convert.cfg'

try: # template of things to do based on repo
    tmp = open( "template.json", "r" )
    tmpRaw = tmp.read( MAXJSON )
    tmp.close()
    templates = json.loads( tmpRaw )
    myLog( "detail", "templates: " + tmpRaw )
except:
    myLog( "error", "Cannot read transform template" )
    sys.exit( 2 )

sp = " "

# decode command line
myLog( "info", "argc: " + str( len( sys.argv )) )

if len( sys.argv ) > 1:
    awsid = sys.argv[1]
else:
    myLog("error", "No AWSID" )
    sys.exit( "510" )

if len( sys.argv ) > 2:
    preConvertBucket = sys.argv[2]
else:
    myLog("error", "No preconvert bucket" )
    sys.exit( "511" )

if len( sys.argv ) > 3:
    api_url = sys.argv[3]
else:
    myLog("error", "No api_url" )
    sys.exit( "512" )

if len( sys.argv ) > 4:
    door43Bucket = sys.argv[4]
else:
    myLog("error", "No door43Bucket" )
    sys.exit( "512" )

if len( sys.argv ) > 5:
    ifle = open( sys.argv[5], "r" )
else:
    ifle = sys.stdin

# decode received message
lines = ifle.readlines()
payload = json.loads( sp.join( lines ) )
myLog( "detail", "notice: " + sp.join( lines ) )
repoName = payload['repository']['name']
myLog( "info", "name: " + repoName )
commitUrl = payload['commits'][0]['url'] 
commitUrl += ".tar.gz"
url = commitUrl.replace( "commit", "archive" )

# verify that url is from git.door43.org
if url.find( ".door43.org" ) < 0:
    myLog( "warning", "Notification is not from Gogs. Ignoring." )
    print( "400" )
    sys.exit( 0 )

myLog( "info", "url: " + url )

s = '/'
pusher = payload[ 'pusher' ][ 'username' ] + s
hash = payload[ 'commits' ][0][ 'id' ][:8] + s
dest =  os.path.join( pusher, repoName, hash )
userToken = payload[ 'secret' ]
myLog( "info", "dest: " + dest + " userToken: " + userToken )

# get collection from repo
zipDir =  inDir # + repoName
zipFile = inDir + repoName + ".tar.gz"
myLog( "info", "  zipDir: " + zipDir )
myLog( "info", "  zipFile: " + zipFile )
orgUmask = os.umask( 0 )

#try: # get repo referenced in notification
if True:
    myLog( "info",  "src: " + url + " dst: " + zipFile )
 
    try:
        if not os.path.exists( zipDir ):
            os.makedirs( zipDir )
        if not os.path.exists( inDir ):
            os.makedirs( inDir )
        download_file( url, zipFile )
 
        try:
             res = subprocess.check_output( 
                 [ "tar", "-xzf", zipFile, "-C", inDir ], 
                 shell=False )
        except( OSError, e ):
            myLog( "error", "cannot tar: " + zipFile +  " Error: " + e.strerror )
            print( "506" )
            sys.exit( 6 )
    except( OSError, e ):
        myLog( "error", "Cannot make working directory: " + zipDir + \
               " Error: " + e.strerror )
        print( "507" )
        sys.exit( 7 )
#except:
#except( OSError, e ):
#    myLog( "error", "Cannot: download " + url + " -o " + zipFile )
#    myLog( "error", "Cannot: curl " + url + " -o " + zipFile + \
#           " Error: " + e.strerror )
#    print( "508" )
#    sys.exit( 8 )

# look through repo because we are curious
os.umask( orgUmask )
orgDir = os.getcwd()
os.chdir( zipDir )
myLog( "info", "pwd: " + os.getcwd() )

if debugLevel > 3: # show all files in repo
    myLog( "info", "files in repo" )

    for root, dirs, files in os.walk( "." ):
        myLog( "detail", "root: " + root )
        #i = 5

        for nme in files:
            srcPath =  join( root, nme )
            myLog( "loops", "file: " + srcPath  )
            #i -= 1

            #if i < 1:
            #    sys.exit(0)

try: # look for repo manifest could be in subdirectory
    mani = "manifest.json"
    myLog( "info", "try to parse:" + mani )
    isMan = "no"

    # read manifest
    if os.path.isfile( mani ):
        mf = open( mani, "r" )
        isMan = "yes"
    elif os.path.isfile( repoName + "/" + mani ):
        mf = open(  repoName + "/" + mani, "r" )
        workDir += repoName + "/"
        isMan = "yes"

    if isMan == "yes":
        raw = mf.read( MAXJSON )
        mf.close()
        myLog( "detail", "have manifest" + raw )
        manifest = json.loads( raw )
    else:
        myLog( "error", "No manifest for this repo." )
        print( "502" )
        sys.exit( 2 )

    # decode manifest
      # Identify doc type
    inputFormat = manifest[ 'format' ]
    myLog( "info", "format: " + inputFormat )

    docType = manifest[ 'source_translations' ][0][ 'resource_id' ]
    myLog( "info", "docType: " + docType )

except( OSError, e ):
    myLog( "error", "Cannot parse manifest. Error: " + e.strerror )
    print( "503" )
    sys.exit( 3 )

#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

pyld = {
        "action": "job",
        "data": {
            "user_token": userToken,
            "resource_type": "tn",
            "input_format": "html",
            "output_format": "pdf",
            "source": url,
            "callback": "https://637mw9ym0i.execute-api.us-west-2.amazonaws.com/sampleclient/callback",
            "options": {
                "page_size": "letter",
                "line_spacing": "120%"
            }
        }
    }

myLog( "detail", "Job: " + json.dumps( pyld ) )

tx = boto3.client( 'lambda' )
#resp = tx.invoke( FunctionName='tx-manager_request', Payload=json.dumps( pyld ))
#payload = json.loads( resp['Payload'].read() )

#if 'errorMessage' in payload:
#    raise Exception( payload )
#else:
#    return{ 'success': True }

#sys.exit( "200" )

#try: # Find doctype in template then process per template
if True:
    isFound = False
    myLog( "info", "looking for docType: " + docType )

    for item in templates[ 'templates']:
        myLog( "detail", "trying: " + item['doctype'] )

        if item['doctype'] == docType:
            myLog( "detail", "found: " + item['doctype'] )

            try: # Apply qualifying tests
                for test in item[ 'tests' ]:
                    myLog( "info", test )
                    #invoke test
            except:
                myLog( "warning", "  Cannot apply tests." )

            #try: # apply transforms from template
            if True:
                fmt =  manifest[ 'type' ][ 'id' ]

                for trans in item[ 'transforms' ]:
                    frm = trans[ 'from' ]
                    myLog( "info",  "fmt: " + fmt + " frm: " + frm )

                    if fmt == frm :
                        if item[ 'agent' ] == 'local': # not using tx use files as is
                            myLog( "detail", "  tool: " + trans[ 'tool' ] )
                            myLog( "detail", "  orgDir: " + orgDir + " current: " + os.getcwd() )
                            os.chdir( orgDir )
                            myLog( "info", "pwd: " + os.getcwd() )
                            tool =  "converters/" + trans[ 'tool' ]
                            source = trans[ 'to' ]
                            myLog( "info", "to: " + trans[ 'to' ] )
                            src = workDir + repoName
                            tgt = outDir + dest + source
                            cmd =  " -s " + src + " -d " + tgt
                            myLog( "info", "cmd: " + tool + " " + cmd )

                            #try:
                            if True: 
                                res = subprocess.check_output( 
                                    [ "python", tool, "-s", src, "-d", tgt ],
                                    stderr=subprocess.STDOUT,
                                    shell=False )
                                myLog( "loops", 'tool result: ' +  res )
                        else:
                            fun = trans[ 'function' ]
                      
                            if fun == 'flatten':
                                tmpFileDir = tempfile.mktemp( prefix='files_' )
                                flatten( os.path.join( inDir,repoName ), tmpFileDir )

                                if trans[ 'to' ] == 'html':
                                    if trans[ 'tool' ] == 'tx':
                                        #txResp = myTx( awsid, tmpFileDir, preConvertBucket, pusher, api_url, payload )
                                        #     def myTx( aswid, massagedFilesDir, preConvertBucket, authorUsername, api_url, data ):
                                      # Zip up the massaged files
                                        zipFilename = awsid + '.zip' # context.aws_request_id is a unique ID 
                                                                         # for this lambda call, so using it to not conflict with other requests
                                        zipFile = os.path.join( tempfile.gettempdir(), zipFilename )
                                        myLog( "info", "zipFile: " + zipFile )
                                        mdFiles = glob(os.path.join( tmpFileDir, '*.md' ))
                                        print('Zipping files from {0} to {1}...'.format( tmpFileDir, zipFile ), end=' ' )
                                        fileCount = 0

                                        for mdFile in mdFiles:
                                           add_file_to_zip(zipFile, mdFile, os.path.basename( mdFile ))
                                           fileCount += 1

                                        print( 'finished zipping: ' + str( fileCount ) + " files." )

                                        # 4) Upload zipped file to the S3 bucket (you may want to do some try/catch 
                                        #    and give an error if fails back to Gogs)
                                        print('Uploading {0} to {1} in {2}...'.format( zipFile, preConvertBucket, zipFilename ), end=' ')
                                        s3Client = boto3.client('s3')
                                        s3Client.upload_file( zipFile, preConvertBucket, zipFilename )
                                        print( 'finished upload.' )
                                      # Send job request to tx-manager
                                        sourceUrl = 'https://s3-us-west-2.amazonaws.com/' + preConvertBucket + '/' + zipFilename # we use us-west-2 for our s3 buckets
                                        txManagerJobUrl = api_url + '/tx/job'
                                        gogsUserToken = payload[ 'secret' ]

                                        txPayload = {
                                            "user_token": gogsUserToken,
                                            "username": pusher,
                                            "resource_type": "obs",
                                            "input_format": "md",
                                            "output_format": "html",
                                            "source": sourceUrl,
                                        }

                                        headers = { "content-type": "application/json"}
                                        print( 'Making request to tx-Manager URL {0} with payload:'.format( txManagerJobUrl ))
                                        print( txPayload )
                                        response = requests.post(txManagerJobUrl, json=txPayload, headers=headers )
                                        print( 'finished tx-manager request.' )

                                      # for testing
                                        print( 'tx-manager response:', end=" " )
                                        print( response )
                                        jsonData = json.loads( response.text )
                                        print( 'jsonData', end=" " )
                                        print( jsonData )
                                        # If there was an error, in order to trigger a 400 error in the API Gateway, we need to raise an
                                        # exception with the returned 'errorMessage' because the API Gateway needs to see 'Bad Request:' in the string
                                        if 'errorMessage' in jsonData:
                                            raise Exception(jsonData['errorMessage'] )

                                        # Unzip ZIP file into the door43Bucket
                                        convertedZipUrl = jsonData['job']['output']
                                        convertedZipFile = os.path.join(tempfile.gettempdir(), convertedZipUrl.rpartition('/')[2])
                                        #========================================

                                        try:
                                            print( 'Downloading converted file from: {0} to: {1} ...'.format( convertedZipUrl, convertedZipFile ), end=' ')
                                            download_file( convertedZipUrl, convertedZipFile )
                                        finally:
                                            print( 'finished download.' )

                                      # Unzip the archive
                                        door43Dir = tempfile.mkdtemp( prefix='door43_' )

                                        if True:
                                        #if os.path.exists( convertedZipFile ):
                                            try:
                                                print( 'Unzipping {0}...'.format( convertedZipFile), end=' ' )
                                                unzip( convertedZipFile, door43Dir )
                                            finally:
                                                print( 'finished unzip.' )
                                            usr = 'u/' + payload['repository']['owner']['username']
                                            s3ProjectKey = os.path.join( usr, repoName, hash )
                                            print( "s3ProjectKey: " + s3ProjectKey )
                                        else:
                                            print( 'Nothing downloaded' )

                                        # Delete existing files in door43.org for this Project Key
                                        s3Resource = boto3.resource( 's3' )
                                        s3Bucket = s3Resource.Bucket( door43Bucket )

                                        for obj in s3Bucket.objects.filter( Prefix=s3ProjectKey ):
                                            s3Resource.Object( s3Bucket.name, obj.key ).delete()

                                        ## Upload all files to the door43 bucket with the key of <user>/<repo_name>/<commit> of the repo
                                        #for root, dirs, files in os.walk(door43Dir):
                                        #    for file in files:
                                        #        path = os.path.join(root, file)
                                        #        key = s3ProjectKey + path.replace(door43Dir, '')
                                        #        s3Client.upload_file(os.path.join(root, file), door43Bucket, key)

                                        # Make a manifest.json file with this repo and commit data for later processing
                                        #manifestFile = os.path.join(tempfile.gettempdir(), 'manifest.json')
                                        #write_file(manifestFile, json.dumps(data))
                                        #s3Client.upload_file(manifestFile, door43Bucket, s3ProjectKey+'/manifest.json')

                                        # Delete the zip files we made above (when we convert to using callbacks, this should be done in the callback)
                                        # Rich: commented out so we can see the file for testing
                                        ##s3Resource.Object(preConvertBucket, zipFilename).delete()

                                        # return something to Gogs response for the webhook. Right now we will just returning the tx-manager response
                                        #return( jsonData )

                            if fun == 'mv_md':
                                mv_md( inDir )
                                fmt = 'md'
                    
                        #except( OSError, e ):
                        #    myLog( "warning", "Cannot run tool: " + tool + " " + \
                        #        cmd + ". Error: " + e.strerror )
            #except:
            #    myLog( "warning", "  Cannot apply transforms" )

            isFound = True
            break

    if isFound == False:
        myLog( "error", "Cannot find docType: " + docIdx )
        print( "504" )
        sys.exit( 4 )

#except:
#    myLog( "error", "No support for docType: " + docType )
#    print( "505" )
#    sys.exit( 5 )

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#try: # Upload to s3
if True:
    s3 = boto3.client( 's3', AWS_REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY )
    boto3.set_stream_logger('botocore', level='DEBUG')
    myLog( "info", "About to upload to bucket: " + door43Bucket + " from: " + outDir )
    os.chdir( outDir )
    src = dest # like "bspidel/gaj-x-ymnk_obs_text_obs/d2bc0dcb/html"
    outPath = bucket + dest
    tpl = 1
    myLog( "info", "cwd: " + os.getcwd() + " src: " + src )

    for root, dirs, files in os.walk( src ):
        myLog( "detail", "root: " + root )
        c = 0

        for nme in files:
            srcPath =  join( root, nme )
            myLog( "loops", "srcPath: " + srcPath +  "  Bucket: " + door43Bucket )  
            s3.upload_file( srcPath, bucket, "u/" + srcPath )
            myLog( "info", "From: " + srcPath + " to: s3://" + door43Bucket + "/u/"  + srcPath )
            c += 1
        
        tpl += c

    myLog( "info",  "Files: " + str( tpl ))

#except( OSError, e ):
#except:
#    myLog( "warning", "Cannot upload to s3. Error: " ) # + e.strerror  )
#    print( "506" )

print( '200' )

if __name__ == "__main__":
    try:
        port_number = int(sys.argv[1])
    except:
        port_number = 80

    is_dev = os.environ.get('ENV', None) == 'dev'

    if os.environ.get('USE_PROXYFIX', None) == 'true':
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

    #app.run( host='0.0.0.0', port=port_number, debug=is_dev )


