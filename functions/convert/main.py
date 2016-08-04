import json
from subprocess import Popen, STDOUT, PIPE

def handle( e, ctx ):
    eventStr = json.dumps( e )
    #print "eventStr: " + eventStr
    p = Popen( [ "python", "convert.py" ], stdin=PIPE, stdout=PIPE, stderr=PIPE )
    res = p.communicate( input=str( eventStr ) ) 
    print( "dump: " + json.dumps( res ) )
    return 0
