FROM lambci/lambda:build-python3.8
ADD common_words.txt /opt/
RUN pip install -t /opt/python/ python-Levenshtein==0.12.2 && \
    pip install -t /opt/python/ fuzzywuzzy==0.18.0  && \
    pip install -t /opt/python/ python-scriptures==3.0.0 && \
    cd /opt && \
    zip -r ../layer.zip *; 
