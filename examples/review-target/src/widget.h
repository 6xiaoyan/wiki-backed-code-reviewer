#ifndef REVIEW_TARGET_WIDGET_H_
#define REVIEW_TARGET_WIDGET_H_

#include <QWidget>

class Widget : public QWidget {
    Q_OBJECT

public:
    explicit Widget(QWidget* parent = nullptr);

signals:
    void valueChanged(int value);

private slots:
    void handleValueChanged(int value);

private:
    int m_value;
};

#endif  // REVIEW_TARGET_WIDGET_H_
