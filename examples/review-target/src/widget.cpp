#include "widget.h"

Widget::Widget(QWidget* parent) : QWidget(parent), m_value(0) {
}

void Widget::handleValueChanged(int value) {
    m_value = value;
    emit valueChanged(value);
}
