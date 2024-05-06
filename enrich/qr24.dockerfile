# use flacy as the starting image
FROM flacy_base:1.0 

# Copy common_words.txt 
RUN mkdir /opt/python
ADD common_words.txt /opt/

# Install Python dependencies
COPY qr24.pip . 
RUN pip3 install -r qr24.pip

# Set an environment variable for the working directory and set it so Docker operates from there
ENV APP /app
RUN mkdir $APP
WORKDIR $APP
# Expose the port uWSGI will listen on
EXPOSE 5000

# Run the python file using uwsgi
CMD [ "uwsgi", "--http-socket", ":5000", "--callable", "app", "--single-interpreter", "--processes", "1", "--wsgi-file", "local-run.py" ]
