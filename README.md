[![Build Status](https://travis-ci.org/unfoldingWord-dev/tX.svg?branch=master)](https://travis-ci.org/unfoldingWord-dev/tX)

Issue queue at https://github.com/unfoldingWord-dev/door43.org/issues

# conv.door43.org

A conversion app for the repos at git.door43.org. Output ends up at [Door43](http://door43.org).
This app should:

 * accept a webhook notification from Gogs,
   * gogs sends notification to AWS API Gateway via: https://livw7majoe.execute-api.us-west-2.amazonaws.com/dev
   * API invokes AWS Lamabda function via functions/convert/main.py
 * pull source content wrapped as ...tar.gz  from respective Gogs repo
   * unzip file
 * identify type of source content (USFM or Markdown) 
   * by reading manifest.json defined in http://discourse.door43.org/t/resource-containers/53, 
   * or by reading file extensions
 * Pass temporary source and target directories to converter function
 * convert into a single HTML page
 * upload to door43 S3 bucket (at same relative URL from Gogs, with some tweaks: /u/[user]/[repo]/[short_commit_hash]/html/index.html)


## Python Requirements

Requirements for a Python script need to reside within the function's directory that calls them.  A requirement for the `convert` function should exist within `functions/convert/`.

The list of requirements for a function should be in a requirements.txt file within that function's directory, for example: functions/convert/requirements.txt.

Requirements *must* be installed before deploying to Lambda.  For example:

    pip install -r functions/convert/requirements.txt -t functions/convert/

The `-t` option tells pip to install the files into the specified target directory.  This ensures that the Lambda environment has direct access to the dependency.

If you have any Python files in subdirectories that also have dependencies, you can import the ones available in the main function by using `sys.path.append('/var/task/')`.

Lastly, if you install dependencies for a function you need to include the following in an .apexignore file:

    *.dist-info

## Lambda function Requirements
* curl
* tar
* s3cmd

## Usage

* Fork or create a repo with manifest defined above
* Add a webhook with url described above
* Clone it to your machine
* Make changes
* Commit then push your changes to repo.
* Examine changes 
  * Use s3ls <key>  
  * Look in door43.org for document converted to HTML

## Tools

* s3rm <key>  -  delete everything under s3://door43.org/u/<key>
* s3ls <key>  -  list every thing under           "        <key>


