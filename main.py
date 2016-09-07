import markdown
import string
import html
import os.path
from flask import Flask,render_template,Markup, request, redirect, url_for

app = Flask(__name__)

@app.route('/pages/<name>')
def wiki_page(name):
	file_name = name.split('.')[0]
	title = fileNameToTitle(file_name)
	#TODO: once we support binary files, turn this into a try-catch
	# and handle the case that it is not a markdown
	if isMarkdown(file_name):
		content = fileNameToHTML(file_name)
		return render_template('wiki_page.html', content=content, title=title)
	else:
		# this should just fail at runtime...
		return send_file(os.path.join('pages',file_name+'.binary'))

# names go like this:
# ' ' -> '_'
# '_' -> '__'
# note that '___' will be '_ ', not ' _' or anything else
# not sure if I care enough to fix this issue...

def fileNameToTitle(fn):
	fn = stripNonPrintable(fn)
	fn = fn.replace('__', '\0')
	fn = fn.replace('_', ' ')
	fn = fn.replace('\0', '_')
	return fn

def titleToFileName(fn):
	fn = stripNonPrintable(fn)
	fn = fn.replace('_', '\0')
	fn = fn.replace(' ', '_')
	fn = fn.replace('\0', '__')
	return fn

def stripNonPrintable(fn):
	out = ''
	for a in fn:
		if a not in string.printable or a in '\t\n\r\x0b\x0c':
			continue
		out+=a
	return out

test_fn = "hello world_of wiki"
assert(test_fn == fileNameToTitle(titleToFileName(test_fn)))


def fileNameToHTML(fn):
	content = fileNameToMarkDown(fn)
	return Markup(markdown.markdown(content))

def fileNameToMarkDown(fn, dirs='pages'):
	full_path = os.path.join(dirs, fn+'.md')
	return fileNameToContent(full_path)

def fileNameToContent(fn):
	with open(fn) as f:
		return f.read()

#@app.route('/edit/<name>/<revision>') # for previous revisions
@app.route('/edit/')
@app.route('/edit/<name>')
def edit_page(name=None, revision=None):
	file_name = name.split('.')[0]
	title = fileNameToTitle(file_name)
	if isMarkdown(file_name):
		content = html.escape(fileNameToMarkDown(file_name))
	else:
		content = "BINARY/UNKNOWN/EMPTY FILE"
	return render_template('edit_page.html', content=content, title=title)

def get_revisions(file_name):
	# list revisions ids and comments
	# going to be listed on the edits page so we can
	# click back to an old revision
	pass

def get_revision_content(file_name, revision_id):
	pass

@app.route('/save/', methods=['POST'])
def save_page():
	name = request.form['title']
	content = request.form.get('content', None)
	fn = titleToFileName(name)
	if 'file' not in request.files:
		save_content(fn, content)
		return redirect(url_for('wiki_page', name=fn))
	files = request.files['file']
	if files.filename == '':
		save_content(fn, content)
		return redirect(url_for('wiki_page', name=fn))
	files.save(os.path.join('pages', fn+'.binary'))
	return redirect(url_for('wiki_page', name=fn))

def save_content(fn, content):
	full_path = os.path.join('pages', fn+'.md')
	with open(full_path, 'w') as f:
		f.write(content)

def isMarkdown(fn):
	#TODO: support non-markdown files...
	return True

if __name__ == "__main__":
	app.run()
