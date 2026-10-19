#ifndef REVIEW_TARGET_DB_H_
#define REVIEW_TARGET_DB_H_

#include <string>

class Database {
public:
    Database();
    ~Database();

    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;

    bool open(const std::string& path);
    void close();

private:
    void* m_handle;
};

#endif  // REVIEW_TARGET_DB_H_
