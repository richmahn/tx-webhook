from __future__ import print_function

import json

from subprocess import Popen, STDOUT, PIPE

def handle( e, ctx ):
    eventStr = json.dumps( e )
    print( "eventStr: " + eventStr )

    if  'pre_convert_bucket' in e:
        preConvertBucket = e[ 'pre_convert_bucket' ]
    else:
        preConvertBucket = ''

    if 'door43Bucket' in e:
        door43Bucket = e[ 'door43Bucket' ]
    else:
        door43Bucket = ''

    if 'api_url' in e:
        api_url = e[ 'api_url' ]
    else:
        api_url = ''

    p = Popen( [ "python", "convert.py", ctx.aws_request_id, preConvertBucket, api_url, bucket ], stdin=PIPE, stdout=PIPE, stderr=PIPE )
    res = p.communicate( input=str( eventStr ) ) 
    print( "dump: " + json.dumps( res ) )
    return 0
