# 使用说明

# 部署脚本使用说明

TODO：需要对照Dockerfile更新

`clone.py`用来获取所有的git仓库    
运行脚本会询问存储的目标路径与其它问题    
推荐先设置`git config --global http.proxy`及git clone ssh的代理    
推荐先设置`http_proxy`, `https_proxy`等环境变量

`env.sh`与`build-ventus.sh`会被`clone.py`复制到目标路径（例如为`./ventus/`）中

先安装所有需要的依赖项
* 已测试环境：ubuntu24.04
* 需要设置`SYSTEMC_HOME`环境变量指向systemc 2.3.4库所在路径
* 需安装verilator >= v5.026版本在$PATH中（建议v5.034）
* 依赖的apt包：
```bash
apt-get install \
    mold ccache ninja-build cmake clang clangd clang-format gdb \
    help2man perl perl-doc flex bison libfl2 libfl-dev zlib1g zlib1g-dev libgoogle-perftools-dev numactl \
    libfmt-dev libspdlog-dev libelf-dev libyaml-cpp-dev device-tree-compiler bsdmainutils ruby default-jdk
```

在目标路径`ventus/`中运行`bash build-ventus.sh`一键编译    

编译完成后，推荐新开终端，设置环境变量：
```bash
cd ventus/
source env.sh
```
可以以不同仿真器作为实际执行后端运行openCL程序：
```bash
cd rodinia/opencl/gaussian
make
./run # 默认使用spike
VENTUS_BACKEND=spike    ./run # 和上一条等效
VENTUS_BACKEND=rtlsim   ./run # 使用verilator仿真Chisel RTL
VENTUS_BACKEND=cyclesim ./run # 使用周期精度仿真器
```

## TODO

现在llvm, gpu-rodinia dataset在组内的服务器上会默认从/home/common/ventus-toolchain-prebuild获取    
没有测试从远程获取时是否也能正确工作

现在必须手动编译安装systemc 2.3.4（组内服务器在`/opt/systemc/2.3.4_dbg_cpp20`）并设置`SYSTEMC_HOME`比较麻烦

没有给build脚本加选项跳过rtlsim与cyclesim，前者编译缓慢，后者需要systemc

现在spike仓库中`fesvr/device.h`缺少`#include <cstdint>`，会编译失败，卡住脚本
