#include <iostream>
#include <string>

#include "db.h"

namespace {

int addNumbers(int left, int right) {
    return left + right;
}

}  // namespace

int main() {
    const std::string storagePath = "storage/data";
    Database database;
    if (!database.open(storagePath)) {
        std::cerr << "failed to open database" << std::endl;
        return 1;
    }
    std::cout << "sum=" << addNumbers(1, 2) << std::endl;
    return 0;
}
