FROM buildpack-deps:24.04 AS ventus-dev-os-base
RUN env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY apt-get update \
    && env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY apt-get upgrade -y \
    && env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY apt-get install -y sudo vim neovim \
       mold ccache ninja-build cmake clang clangd clang-format gdb \
       help2man perl perl-doc flex bison libfl2 libfl-dev zlib1g zlib1g-dev libgoogle-perftools-dev numactl \
       libfmt-dev libspdlog-dev libelf-dev libyaml-cpp-dev device-tree-compiler bsdmainutils ruby default-jdk \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && adduser ubuntu sudo

FROM ventus-dev-os-base AS builder_systemc
WORKDIR /tmp/systemc
RUN curl -LO https://github.com/accellera-official/systemc/archive/refs/tags/2.3.4.tar.gz \
    && tar -xzf 2.3.4.tar.gz --strip-components=1 \
    && ./config/bootstrap \
    && mkdir build && cd build \
    && ../configure 'CXXFLAGS=-std=c++20' --enable-debug --prefix=/opt/systemc/2.3.4_cpp20_dbg \
    && make -j$(nproc) \
    && make install

FROM ventus-dev-os-base AS builder_verilator
WORKDIR /tmp/verilator
RUN git clone https://github.com/verilator/verilator \
    && cd verilator \
    && git checkout v5.034 \
    && autoconf \
    && ./configure --prefix=/opt/verilator/5.034 \
    && make -j$(nproc) \
    && make test \
    && make install

FROM ventus-dev-os-base AS ventus-dev-os-merge-tmp
COPY --from=builder_systemc /opt/systemc/2.3.4_cpp20_dbg /opt/systemc/2.3.4_cpp20_dbg
COPY --from=builder_verilator /opt/verilator/5.034 /opt/verilator/5.034

FROM ventus-dev-os-base AS ventus-dev-os
COPY --from=ventus-dev-os-merge-tmp /opt /opt

FROM ventus-dev-os AS ventus-dev-repo-clone
USER ubuntu
WORKDIR /home/ubuntu/ventus
ENV PATH="/opt/verilator/5.034/bin:${PATH}"
ENV SYSTEMC_HOME="/opt/systemc/2.3.4_cpp20_dbg"
COPY --chown=ubuntu:ubuntu ./build-ventus.sh ./env.sh ./spike.patch ./
RUN echo "export PATH=\"/opt/verilator/5.034/bin:\${PATH}\"" >> /home/ubuntu/.bashrc \
    && echo "export SYSTEMC_HOME=\"/opt/systemc/2.3.4_cpp20_dbg\"" >> /home/ubuntu/.bashrc \
    && git clone --recursive -b main --depth=10 https://github.com/THU-DSP-LAB/llvm-project.git llvm \
    && git clone --recursive -b dev-devices https://github.com/THU-DSP-LAB/pocl.git pocl \
    && git clone --recursive -b dev-devices https://github.com/THU-DSP-LAB/ventus-driver.git driver \
    && git clone --recursive -b regression-test https://github.com/THU-DSP-LAB/gpu-rodinia.git rodinia \
    && git clone --recursive -b dev-2024 https://github.com/THU-DSP-LAB/ventus-gpgpu.git gpgpu \
    && git clone --recursive -b develop https://github.com/THU-DSP-LAB/ventus-gpgpu-cpp-simulator.git simulator \
    && git clone --recursive https://github.com/THU-DSP-LAB/ventus-gpgpu-isa-simulator.git spike \
    && git clone --recursive https://github.com/OCL-dev/ocl-icd ocl-icd \
    && patch spike/fesvr/device.h < spike.patch
COPY --chown=ubuntu:ubuntu ./rodinia/data /home/ubuntu/ventus/rodinia/data

FROM ventus-dev-repo-clone AS ventus-dev-llvm
USER ubuntu
WORKDIR /home/ubuntu/ventus
RUN bash build-ventus.sh --build llvm

FROM ventus-dev-llvm AS ventus-dev-spike
USER ubuntu
WORKDIR /home/ubuntu/ventus
RUN bash build-ventus.sh --build ocl-icd \
    && bash build-ventus.sh --build libclc \
    && bash build-ventus.sh --build spike

FROM ventus-dev-spike AS ventus-dev-rtlsim
USER ubuntu
WORKDIR /home/ubuntu/ventus
ENV SHELL=/bin/bash
RUN bash build-ventus.sh --build rtlsim

FROM ventus-dev-rtlsim AS ventus-dev-cyclesim
USER ubuntu
WORKDIR /home/ubuntu/ventus
RUN bash build-ventus.sh --build cyclesim

FROM ventus-dev-cyclesim AS ventus-dev
USER ubuntu
WORKDIR /home/ubuntu/ventus
RUN bash build-ventus.sh --build driver \
    && bash build-ventus.sh --build pocl \
    && bash build-ventus.sh --build rodinia \
    && bash build-ventus.sh --build test-pocl

# FROM ventus-dev-repo-clone AS ventus-dev
# USER ubuntu
# WORKDIR /home/ubuntu/ventus
# SHELL ["/bin/bash", "-c"]
# RUN bash build-ventus.sh

FROM ventus-dev-os AS ventus
USER ubuntu
WORKDIR /home/ubuntu/ventus
COPY --chown=ubuntu:ubuntu --from=ventus-dev ./install ./
