FROM jupyter/scipy-notebook

USER root
# Generally, Dev Container Features assume that the non-root user (in this case jovyan)
# is in a group with the same name (in this case jovyan). So we must first make that so.
RUN groupadd jovyan \
    && usermod -g jovyan -a -G users jovyan

USER jovyan
COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/
# RUN conda install --yes --file /tmp/requirements.txt && \
#     conda clean --all -f -y && \
#     fix-permissions "${CONDA_DIR}" && \
#     fix-permissions "/home/${NB_USER}"