cmake_minimum_required(VERSION 3.16)
project(review_target LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(review_target
    src/main.cpp
    src/db.cpp
    src/legacy.cpp
)

# Qt 示例（需要本机安装 Qt6 才能构建；PR 审查不要求构建）
# find_package(Qt6 COMPONENTS Widgets REQUIRED)
# target_sources(review_target PRIVATE src/widget.cpp)
# target_link_libraries(review_target PRIVATE Qt6::Widgets)
