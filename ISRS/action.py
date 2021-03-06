from functools import reduce
from flask import (
    Blueprint, redirect, render_template, request, url_for, g, jsonify, abort, Response, current_app, send_from_directory
)

import csv

from ISRS.auth import force_login
from ISRS.model import db, User, Sheet, Question
from ISRS.color import colors


bp = Blueprint('action', __name__, url_prefix='/action')

@bp.route('/gen/', methods=['OPTIONS'])
def gen_option():
    res = Response("OK")
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return res

@bp.route('/gen/', methods=('GET', 'POST'), provide_automatic_options=False)
@force_login('action.generate_sheet')
def generate_sheet():
    """
        Get data of generated sheet
    """
    if request.method == 'POST':
        new_sheet = request.get_json()

        user = User.query.filter_by(id=g.user.id).first()
        sheet = Sheet(sheet_type=new_sheet['sheet_type'],
                      title=new_sheet['sheet_title'],
                      question_number=new_sheet['total_ques_num'],
                      option_number=new_sheet['total_opt_num'],
                      footer=new_sheet['sheet_footer'],
                      users=user)
        for question in new_sheet['ques_set']:
            Question(question_order=question['prob_num'],
                     question_title=question['problem'],
                     option_title=question['options'],
                     sheets=sheet)
        db.session.add(sheet)
        db.session.commit()

        res = redirect(url_for('action.list_sheet'))
        res.headers['Access-Control-Allow-Origin'] = '*'

        return res

    # TODO: store JSON data into sheet table
    # return redirect(url_for('action.list_sheet'))

    return render_template('template.html')

@bp.route('/edit/<sheet_id>/', methods=['OPTIONS'])
def edit_option(sheet_id):
    res = Response("OK")
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return res

@bp.route('/edit/<sheet_id>/', methods=('GET', 'POST'), provide_automatic_options=False)
@force_login('action.update_sheet')
def update_sheet(sheet_id):
    """
        Get data of generated sheet
    """
    if request.method == 'POST':
        new_sheet = request.get_json()

        sheet = Sheet.query.filter_by(id=sheet_id).first()
        sheet.sheet_type=new_sheet['sheet_type']
        sheet.title=new_sheet['sheet_title']
        sheet.question_number= new_sheet['total_ques_num']
        sheet.option_number = new_sheet['total_opt_num']
        sheet.footer=new_sheet['sheet_footer']

        for removed_question in sheet.questions:
            db.session.delete(removed_question)

        for removed_response in sheet.responses:
            db.session.delete(removed_response)

        db.session.commit()

        for question in new_sheet['ques_set']:
            Question(question_order=question['prob_num'],
                     question_title=question['problem'],
                     option_title=question['options'],
                     sheets=sheet)

        db.session.add(sheet)
        db.session.commit()

        res = redirect(url_for('action.list_sheet'))
        res.headers['Access-Control-Allow-Origin'] = '*'
        return res

    return render_template('edit.html', sheet_id=sheet_id)

@bp.route('/edit_json/<sheet_id>/', methods=('GET',))
@force_login('action.update_sheet_json')
def update_sheet_json(sheet_id):
    sheet = Sheet.query.filter_by(id=sheet_id).first()
    return jsonify(
        sheet_title=sheet.title,
        sheet_footer=sheet.footer,
        sheet_type=sheet.sheet_type,
        total_ques_num=sheet.question_number,
        total_opt_num=sheet.option_number,
        ques_set=[
            {
                "prob_num": i + 1,
                "problem": sheet.questions[i].question_title,
                "options" : [
                    {
                        "opt_num": j + 1,
                        "description": option
                    } for j, option in enumerate(sheet.questions[i].option_title)
                ]
            } for i in range(len(sheet.questions))
        ]
    )

@bp.route('/list/', methods=('GET',))
@force_login('action.list_sheet')
def list_sheet():
    """
        List sheet which belong to logged-in user
    """
    # TODO: Return all sheet of logged-in user
    # TODO
    return render_template('list.html', list='menu-active')

    # return '<h1 style="text-align: center;">List Sheet</h1>'

@bp.route('/list_json/', methods=('GET',))
@force_login('action.list_sheet_json')
def list_sheet_json():
    """ JSON response about sheet of specific user """
    print(colors.GREEN + 'List : User ' + str(g.user.id) + colors.END)
    user = User.query.filter_by(id=g.user.id).first()
    sheets = user.sheets

    sheet_ids = list(reversed([sheet.id for sheet in sheets]))
    sheet_titles = list(reversed([sheet.title for sheet in sheets]))

    return jsonify(sheet_ids=sheet_ids,
                   sheet_titles=sheet_titles
                  )


@bp.route('/visualize/<sheet_id>/', methods=('GET',))
@force_login('action.visualize_sheet')
def visualize_sheet(sheet_id):
    """
        Visualize specific sheet
    """

    # TODO : check 'sheet_id' whether belong to current logged-in user
    return render_template('result.html', sheet_id=sheet_id)

    #return '<h1 style="text-align: center;">Visualize' + sheet_id + '</h1>'

@bp.route('/visualize_json/<sheet_id>/', methods=('GET',))
@force_login('action.visualize_sheet_json')
def visualize_sheet_json(sheet_id):
    """ JSON response about sheet of specific user """
    sheet = Sheet.query.filter_by(id=sheet_id).first()

    # No this sheet id
    if sheet is None:
        abort(404)

    if g.user.id == sheet.user_id:

        # if everything is empty ?
        question_titles = [question.question_title for question in sheet.questions]
        response_conclude = [
            [
                {
                    'description': option_title,
                    'value': 0,
                } for option_title in question.option_title
            ] for question in sheet.questions
        ]

        for response in sheet.responses:
            print(response.created_at)
            for i, choose in enumerate(response.response_list):
                response_conclude[i][choose-1]['value'] += 1

        return jsonify(title=sheet.title,
                       question_title=question_titles,
                       response_conclude=response_conclude
                      )

    # sheet does not belong to this user
    abort(401)

@bp.route('/response_csv/<sheet_id>/', methods=('GET',))
@force_login('action.response_csv')
def response_csv(sheet_id):
    """
        Return csv file response
        filename: sheet_title.csv
    """
    sheet = Sheet.query.filter_by(id=sheet_id).first()
    if sheet.responses == []:
        return render_template('result.html', sheet_id=sheet_id, no_response=True)

    # set column header
    field_name = ['問題']
    for i in range(1, len(max(sheet.questions, key=lambda question: len(question.option_title)).option_title)+1):
        field_name += ['選項'+str(i)+'內容'] + ['選項'+str(i)+'總回答數']

    #[question][choosed_option]
    response_conclude = [[0 for _ in range(len(question.option_title))] for question in sheet.questions]
    for response in sheet.responses:
        for i, choose in enumerate(response.response_list):
            response_conclude[i][choose-1] += 1

    # 2D-array data
    csv_data = [
                [question.question_title] + list(
                                                    reduce(
                                                            (lambda i,j: i+j),
                                                            zip(
                                                                question.option_title,
                                                                conclude
                                                               )
                                                          )
                                                )
                for question, conclude in zip(sheet.questions, response_conclude)
               ]

    single_field_name = ['得到回覆結果之時間'] + [question.question_title for question in sheet.questions]
    single_csv_data = [[response.created_at.strftime('%Y/%m/%d %H:%M:%S')] + response.response_list for response in sheet.responses]

    with open(current_app.config['CSV_FOLDER']+sheet.title+'.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(field_name)
        writer.writerows(csv_data)

        writer.writerows([[] for _ in range(3)])

        writer.writerow(single_field_name)
        writer.writerows(single_csv_data)


    return send_from_directory(directory=current_app.config['CSV_FOLDER'],
                               filename=sheet.title+'.csv',
                               as_attachment=True,
                              )

@bp.route('/about/', methods=('GET',))
def about():
    return render_template('about.html', about='menu-active')

@bp.route('/admin')
def list_user():
    users = User.query.all()
    data = dict(username=[user.username for user in users],
                password=[user.password for user in users])
    return jsonify(data)
