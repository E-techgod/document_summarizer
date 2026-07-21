# The {{}} needs to match whe using jinja2, if using replace then use {}
SUMMARY_TEMPLATE= """
Please summarize the following document cleanly:  
{{ document_text }} 
"""