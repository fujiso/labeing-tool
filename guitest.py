
# coding: utf-8

import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from maketag import Ui_MakeTag
from pymongo import MongoClient
import configparser


config = configparser.ConfigParser()
config.read('config.txt')
database = config["database"]
condition = config["condition"]
feature = [config["feature"]["f{}".format(i)] for i in range(len(config["feature"]))]


class Test(QMainWindow):
    data_list = []
    list_index = 0

    def __init__(self, parent=None):
        super(Test, self).__init__(parent)

        self.ui = Ui_MakeTag()
        self.Maketag = self.ui.setupUi(self)
        # データベースの設定
        self.db_name = database["db"]
        self.col_name = database["col"]
        self.client = MongoClient(database["host"], 27017)
        self.db = self.client[self.db_name]
        self.col = self.db[self.col_name]

        self.feature_list = feature
        self.feature_key = database["key"]
        self.cond = dict(condition)

        self.merge_dict = lambda a, b: a.update(b) or a
        # タグ付け終わったものを操作するかのフラグ 操作しない = True
        self.flag = True
        # 左上：　現在開いているdbの名前表示
        self.ui.label.setText(
            "<html><head/><body><p><span style=\" font-size:11pt;\">\
            ＤＢ：{db}</span></p></body></html>".format(db=self.db_name))
        self.ui.label_4.setText(
            "<html><head/><body><p><span style=\" font-size:11pt;\">\
            Collection:{col}</span></p></body></html>".format(col=self.col_name))

        # 左上： 商品名のリストを表示
        for (num, product) in enumerate(self.col.find().distinct("product")):
            item = QListWidgetItem()
            self.ui.listWidget.addItem(item)
            item = self.ui.listWidget.item(num)
            item.setText(product)
            # 一つの商品すべてにタグ付けが終わっている場合、グレー背景にする
            if not self.col.count(
                    self.merge_dict({"product": product, "tagged": False}, self.cond)):
                item.setBackground(QColor(150, 150, 150))

        # 先頭の要素を被選択状態にする（エラー防止）
        self.ui.listWidget.setCurrentItem(self.ui.listWidget.item(0))
        self.ui.textBrowser.setText("商品を選択してください。")

        self.ui.textBrowser_1.setText(self.feature_list[0])
        self.ui.textBrowser_2.setText(self.feature_list[1])
        self.ui.textBrowser_3.setText(self.feature_list[2])
        self.ui.textBrowser_4.setText(self.feature_list[3])
        self.ui.textBrowser_5.setText(self.feature_list[4])
        self.ui.textBrowser_6.setText(self.feature_list[5])
        self.ui.pushButton.clicked.connect(self.goNext)
        self.ui.pushButton_2.clicked.connect(self.selectProduct)
        self.ui.pushButton_3.clicked.connect(self.dropout)
        self.ui.actionFihish.triggered.connect(self.exit)
        self.ui.checkBox.clicked.connect(self.changeFlag)

    def selectProduct(self):
        """(lambda a,b: a.update(b) or a)({'a':1, 'b':3},{'c':5})
        左上に配置いてある決定ボタンを押したときに、実行される。
        横のツリータブで選択されている商品のドキュメントを読み込み、必要な情報を表示する。

        """
        # 決定ボタンが押された際に選択されていた商品名を取得する
        self.nowitem = self.ui.listWidget.selectedItems()[0]
        product = self.nowitem.text()
        # 初期化
        self.data_list = []
        self.list_index = 0
        # データベースから商品の読み込み
        if self.flag:
            for data in self.col.find({"product": product, "tagged": False}.update(self.cond)):
                self.data_list.append(data)
        else:
            for data in self.col.find({"product": product}.update(self.cond)):
                self.data_list.append(data)

        # 選択した商品についての情報の表示
        self.ui.label_product.setText("product:{pro}".format(pro=product))
        self.ui.label_all.setText("総数:{all}".format(
            all=self.col.count(self.merge_dict({"product": product}, self.cond))))
        self.ui.label_tagged.setText("済：{tagged}".format(
            tagged=self.col.count(
                self.merge_dict({"product": product, "tagged": True}, self.cond))))
        # データセットが空の時
        if not self.data_list:
            self.ui.textBrowser.setText(
                "この商品のタグ付けは終了しています。")
            self.nowitem.setBackground(QColor(150, 150, 150))

            return

        # 最初のレビュー本文の表示
        self.ui.textBrowser.setText("<html><head/><body><p><span style=\" font-size:13pt;\">\
            {rev}</span></p></body></html>".format(rev=self.data_list[0]["review"]))
        self.ui.label_5.setText("評価：{star}".format(
            star=self.data_list[0]["star"]))

    def goNext(self):
        """
        ボタン「次へ」を押したときに呼び出される。

        タグ付したデータをデータベースに反映して、
        次のレビューを読み込む
        """
        # アイテム名の取得
        product = self.nowitem.text()
        # タグ付終了時
        if self.col.count({"product": product, "tagged": True}.update(self.cond))\
                == self.col.count({"product": product}.update(self.cond)):
            self.ui.textBrowser.setText("この商品のタグ付けは終了しています。")
            self.ui.label_tagged.setText("済：{tagged}".format(
                tagged=self.col.count({"product": product, "tagged": True}.update(self.cond))))
            self.nowitem.setBackground(QColor(150, 150, 150))
            return

        # タグ付未完了のまま最後まで来たとき、またはデータ読み込み前にボタンを押したとき
        if self.list_index >= len(self.data_list) or not self.data_list:
            self.ui.textBrowser.setText("異常が発生しました。もう一度商品を選択して決定ボタンを押してください")
            return

        # 入力をDBに反映させる
        dic = {}
        data = self.data_list[self.list_index]
        label = self.checkRadioBotton()
        for (f, l) in zip(self.feature_list, label):
            dic[f] = l
        data["tagged"] = True
        data[self.feature_key] = dic
        self.col.save(data)

        # リストのインデックスを次に送る
        self.list_index += 1

        # タグ付終了時
        if self.col.count({"product": product, "tagged": True}.update(self.cond))\
                == self.col.count({"product": product}.update(self.cond)):
            self.ui.textBrowser.setText("この商品のタグ付けは終了です。お疲れ様でした。")
            self.ui.label_tagged.setText("済：{tagged}".format(
                tagged=self.col.count({"product": product, "tagged": True}.update(self.cond))))
            self.nowitem.setBackground(QColor(150, 150, 150))
            return

        # ラジオボタンをリセットする
        # もしタグ付すみのを読み込むのであれば、工夫する
        self.ui.radioButton_1none.setChecked(True)
        self.ui.radioButton_2none.setChecked(True)
        self.ui.radioButton_3none.setChecked(True)
        self.ui.radioButton_4none.setChecked(True)
        self.ui.radioButton_5none.setChecked(True)
        self.ui.radioButton_6none.setChecked(True)
        if self.list_index < len(self.data_list):
            nextdata = self.data_list[self.list_index]
            # self.resetRadioBotton(nextdata)
            self.ui.textBrowser.setText(
                "<html><head/><body><p><span style=\" font-size:13pt;\">\
                {rev}</span></p></body></html>".format(
                    rev=nextdata["review"]))
            self.ui.label_5.setText("評価：{star}".format(
                star=nextdata["star"]))
        self.ui.label_tagged.setText("済：{tagged}".format(
            tagged=self.col.count({"product": product, "tagged": True}.update(self.cond))))

    def dropout(self):
        product = self.nowitem.text()
        data = self.data_list[self.list_index]
        self.col.remove(data)
        # リストのインデックスを次に送る
        self.list_index += 1

        # タグ付終了時
        if self.col.count({"product": product, "tagged": True}.update(self.cond))\
                == self.col.count({"product": product}.update(self.cond)):
            self.ui.textBrowser.setText("この商品のタグ付けは終了です。お疲れ様でした。")
            self.ui.label_all.setText("総数:{all}".format(
                all=self.col.count({"product": product}.update(self.cond))))
            self.nowitem.setBackground(QColor(150, 150, 150))
            return

        # ラジオボタンをリセットする
        # もしタグ付済みのを読み込むのであれば、工夫する
        self.ui.radioButton_1none.setChecked(True)
        self.ui.radioButton_2none.setChecked(True)
        self.ui.radioButton_3none.setChecked(True)
        self.ui.radioButton_4none.setChecked(True)
        self.ui.radioButton_5none.setChecked(True)
        self.ui.radioButton_6none.setChecked(True)
        if self.list_index < len(self.data_list):
            nextdata = self.data_list[self.list_index]
            # self.resetRadioBotton(nextdata)
            self.ui.textBrowser.setText(
                "<html><head/><body><p><span style=\" font-size:13pt;\">\
                {rev}</span></p></body></html>".format(
                    rev=nextdata["review"]))
            self.ui.label_5.setText("評価：{star}".format(
                star=nextdata["star"]))
        self.ui.label_all.setText("総数:{all}".format(
            all=self.col.count({"product": product}.update(self.cond))))

    def changeFlag(self):
        """
        チェックボタンが押されたときに動作。
        フラグを変更して、表示に反映させる。
        """
        self.flag = self.ui.checkBox.isChecked()
        self.selectProduct()

    def exit(self):
        """
        アプリケーションを終了する
        """
        self.client.close()
        sys.exit(QApplication(sys.argv).quit)

    def checkRadioBotton(self):
        """
        ラジオボタンを読み取り、付けたラベルのリストを作成する。
        """
        label = [0, 0, 0, 0, 0, 0]
        if self.ui.radioButton_1pos.isChecked():
            label[0] = 1
        elif self.ui.radioButton_1neg.isChecked():
            label[0] = -1

        if self.ui.radioButton_2pos.isChecked():
            label[1] = 1
        elif self.ui.radioButton_2neg.isChecked():
            label[1] = -1

        if self.ui.radioButton_3pos.isChecked():
            label[2] = 1
        elif self.ui.radioButton_3neg.isChecked():
            label[2] = -1

        if self.ui.radioButton_4pos.isChecked():
            label[3] = 1
        elif self.ui.radioButton_4neg.isChecked():
            label[3] = -1

        if self.ui.radioButton_5pos.isChecked():
            label[4] = 1
        elif self.ui.radioButton_5neg.isChecked():
            label[4] = -1

        if self.ui.radioButton_6pos.isChecked():
            label[5] = 1
        elif self.ui.radioButton_6neg.isChecked():
            label[5] = -1

        return label

    def resetRadioBotton(self, data):
        """
        ラジオボタンをリセットする

        args:
            data: 次に表示させたいデータ
        """
        # ダグ付けしていないデータしか扱わない時 (チェックボックスon)
        if self.flag:
            self.ui.radioButton_1none.setChecked(True)
            self.ui.radioButton_2none.setChecked(True)
            self.ui.radioButton_3none.setChecked(True)
            self.ui.radioButton_4none.setChecked(True)
            self.ui.radioButton_5none.setChecked(True)
            self.ui.radioButton_6none.setChecked(True)

        # すべてのデータを扱う時 (チェックボックスoff)
        else:
            # タグ付けしていない場合、data["feature"]は空辞書になっている
            # タグ付け済みの場合、データの読み込み
            if data["feature"]:
                fdic = data["feature"]
                if fdic[self.feature_list[0]] == 1:
                    self.ui.radioButton_1pos.setChecked(True)
                elif fdic[self.feature_list[0]] == -1:
                    self.ui.radioButton_1neg.setChecked(True)
                else:
                    self.ui.radioButton_1none.setChecked(True)

                if fdic[self.feature_list[1]] == 1:
                    self.ui.radioButton_2pos.setChecked(True)
                elif fdic[self.feature_list[1]] == -1:
                    self.ui.radioButton_2neg.setChecked(True)
                else:
                    self.ui.radioButton_2none.setChecked(True)

                if fdic[self.feature_list[2]] == 1:
                    self.ui.radioButton_3pos.setChecked(True)
                elif fdic[self.feature_list[2]] == -1:
                    self.ui.radioButton_3neg.setChecked(True)
                else:
                    self.ui.radioButton_3none.setChecked(True)

                if fdic[self.feature_list[3]] == 1:
                    self.ui.radioButton_4pos.setChecked(True)
                elif fdic[self.feature_list[3]] == -1:
                    self.ui.radioButton_4neg.setChecked(True)
                else:
                    self.ui.radioButton_4none.setChecked(True)

                if fdic[self.feature_list[4]] == 1:
                    self.ui.radioButton_5pos.setChecked(True)
                elif fdic[self.feature_list[4]] == -1:
                    self.ui.radioButton_5neg.setChecked(True)
                else:
                    self.ui.radioButton_5none.setChecked(True)

                if fdic[self.feature_list[5]] == 1:
                    self.ui.radioButton_6pos.setChecked(True)
                elif fdic[self.feature_list[5]] == -1:
                    self.ui.radioButton_6neg.setChecked(True)
                else:
                    self.ui.radioButton_6none.setChecked(True)
            # タグ付けできていない場合、すべてnoneにセット
            else:
                self.ui.radioButton_1none.setChecked(True)
                self.ui.radioButton_2none.setChecked(True)
                self.ui.radioButton_3none.setChecked(True)
                self.ui.radioButton_4none.setChecked(True)
                self.ui.radioButton_5none.setChecked(True)
                self.ui.radioButton_6none.setChecked(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Test()
    window.show()
    sys.exit(app.exec_())
