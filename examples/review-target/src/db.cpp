#include "db.h"

#include <sqlite3.h>

namespace {

constexpr int KDF_ITERATIONS = 256000;
constexpr int BUSY_TIMEOUT_MS = 5000;

}  // namespace

Database::Database() : m_handle(nullptr) {
}

Database::~Database() {
    close();
}

bool Database::open(const std::string& path) {
    sqlite3* handle = nullptr;
    if (sqlite3_open(path.c_str(), &handle) != SQLITE_OK) {
        return false;
    }
    m_handle = handle;

    const char* keyStatement = "PRAGMA key = 'review-target-demo';";
    if (sqlite3_exec(handle, keyStatement, nullptr, nullptr, nullptr) != SQLITE_OK) {
        return false;
    }
    const char* kdfStatement =
        "PRAGMA cipher_default_kdf_iter = 256000;";
    if (sqlite3_exec(handle, kdfStatement, nullptr, nullptr, nullptr) != SQLITE_OK) {
        return false;
    }
    sqlite3_busy_timeout(handle, BUSY_TIMEOUT_MS);
    return true;
}

void Database::close() {
    if (m_handle != nullptr) {
        sqlite3_close(static_cast<sqlite3*>(m_handle));
        m_handle = nullptr;
    }
}
