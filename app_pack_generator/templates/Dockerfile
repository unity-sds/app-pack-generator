FROM jupyter/base-notebook

ENV HOME=/home/$NB_USER

WORKDIR $HOME/hello-world

USER root

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git
    
RUN pip install papermill

USER $NB_USER

ADD https://api.github.com/repos/marjo-luc/hello-world/git/refs/heads/main version.json

RUN git clone https://github.com/marjo-luc/hello-world.git

RUN cd hello-world

RUN python -c "import black; black.cache.CACHE_DIR.mkdir(parents=True, exist_ok=True)"

CMD ["/bin/bash"]
