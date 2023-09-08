FROM qrbible_enrich_loc_proto:1.4

# Set an environment variable for the working directory and set it so Docker operates from there
ENV APP /app
RUN mkdir $APP
WORKDIR $APP

# Copy the python app and the common_words file
COPY common_words.txt .
COPY closest_bible_book.py .
COPY enrich_text.py .
COPY local-run.py .

# Install postgres because you will need it for populating congregations, torah portions
RUN pip3 install psycopg2-binary==2.9.3

# Expose the port uWSGI will listen on
EXPOSE 5000

# Run the python file using uwsgi
CMD [ "uwsgi", "--http-socket", ":5000", "--callable", "app", "--single-interpreter", "--processes", "1", "--wsgi-file", "local-run.py" ]
