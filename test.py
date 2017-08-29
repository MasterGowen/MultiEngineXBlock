# -*- coding: utf-8 -*-
import copy
student_answer = {"id8DC0D34E":["idE47DC98C"],"id57B65573":[],"idD802533D":["id48E7C0C8", "id856B4E82"]}
correct_answer = {"idE4D12E77": [], "idAB01EF9A": [], "idC22FEDE6": {"or": [["idC22FEDE6_359"], ["idC22FEDE6_360"], ["idC22FEDE6_361"], ["idC22FEDE6_362"], ["idC22FEDE6_363"], ["idC22FEDE6_179"], ["idC22FEDE6_180"], ["idC22FEDE6_181"], ["idC22FEDE6_182"], ["idC22FEDE6_183"]]}, "id8993373C": [], "id05BA065A": {"or": [["id05BA065A_88"], ["id05BA065A_89"], ["id05BA065A_90"], ["id05BA065A_91"], ["id05BA065A_92"]]}, "id71723C22": {"or": [["id71723C22_270"], ["id71723C22_271"], ["id71723C22_272"], ["id71723C22_273"], ["id71723C22_274"]]}, "id29BE0076": [], "id2C34C555": [], "id41423ADA": [], "id4F660366": [], "id8EAD810E": {"or": [["id8EAD810E_114"], ["id8EAD810E_115"], ["id8EAD810E_116"], ["id8EAD810E_117"], ["id8EAD810E_118"]]}, "id5D683B2D": {"or": [["id5D683B2D_89"], ["id5D683B2D_90"], ["id5D683B2D_91"], ["id5D683B2D_92"], ["id5D683B2D_93"]]}, "id8BB17DC4": [], "id20685025": [], "id7BE6D119": [], "idE6DC2D1B": [], "id484CE10F": []}

keywords = ('or', 'and', 'not', 'or-and')


def max_length(lst):
    length = 0
    for element in lst:
        if len(element) > length:
            length = len(element)
    return length


def _compare_answers_not_sequenced(student_answer, correct_answer, checked=0, correct=0):

    fail = False

    right_answers = []
    wrong_answers = []

    correct_answers_list = []
    student_answers_list = []
    for key in student_answer:
        student_answers_list += student_answer[key]

    for key in correct_answer:
        for value in correct_answer[key]:
            with_keyword = False
            if value in keywords:
                if value == "or":
                    keyword = value
                    correct_values = correct_answer[key][keyword]
                    for correct_value in correct_values:
                        correct_answers_list += correct_value
                        if len(set(correct_value) - set(student_answer[key])) == 0:
                            with_keyword = True
                            break
                    if with_keyword:
                        checked += len(student_answer[key])
                        correct += len(student_answer[key])
                    else:
                        checked += len(student_answer[key])
                elif value == "or-and":
                    keyword = value
                    max_points_current = 0
                    correct_variant_len = 0
                    checked_objects = []
                    student_answer_key = set(student_answer[key])
                    for obj in correct_answer[key][keyword]:
                        if len(set(obj)) > max_points_current:
                            max_points_current = len(set(obj))

                    max_entry_variant = 0
                    for obj in correct_answer[key][keyword]:

                        correct_answers_list += obj

                        if max_entry_variant < len(set(obj)):
                            max_entry_variant = len(set(obj))
                            correct_variant_len = max_points_current = len(correct_answer[key][keyword])

                        for answer in copy.deepcopy(student_answer_key):

                            if answer in obj and obj not in checked_objects:
                                correct += 1
                                checked_objects.append(obj)
                            elif answer not in obj:
                                pass
                            else:
                                fail = True
                    checked += correct_variant_len

            elif value in student_answer[key]:
                correct_answers_list.append(value)
                right_answers.append(value)
                checked += 1
                correct += 1
            else:
                correct_answers_list.append(value)
                wrong_answers.append(value)
                checked += 1

    if len(set(student_answers_list) - set(correct_answers_list)) or fail:
        print(set(student_answers_list))
        print(set(correct_answers_list))
        correct = 0

    checks = {"result": correct / float(checked),
              "right_answers": right_answers,
              "wrong_answers": wrong_answers,
              "checked": checked
              }
    return checks


print(_compare_answers_not_sequenced(student_answer, correct_answer, checked=0, correct=0))