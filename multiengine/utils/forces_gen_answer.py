import json

student_state =  {"iF":["xiF_90","xiF_0"],"iE":["iE_90"]}
tolerances = {}


def _revert_arrow(variant):
    if variant[0] == 'x':
        return True
    else:
        return False

for key in student_state:
    tolerances[key] = {}
    or_dict = {}
    or_dict["or-and"] = []
    for variant in student_state[key]:
        tolerance = [[-1, 0, 1]]

        if _revert_arrow(variant):
            tmp_tolerance = []
            for delta in tolerance[0]:
                tmp_tolerance.append(180 + delta)
                variant = variant.replace('x', '')
            tolerance.append(tmp_tolerance)

        tolerances[key][variant] = tolerance

        variant = variant.split('_')

        variant_list = []
        for tolerance_item in tolerance:
            for delta in tolerance_item:
                if int(variant[1]) + delta >= 360:
                    variant_list.append(variant[0] + '_' + str(int(variant[1]) + delta - 360))
                elif int(variant[1]) + delta < 0:
                    variant_list.append(variant[0] + '_' + str(int(variant[1]) + delta + 360))
                else:
                    variant_list.append(variant[0] + '_' + str(int(variant[1]) + delta))

        or_dict["or-and"].append(variant_list)


        student_state[key] = or_dict
answer = {}
answer["answer"] = student_state
answer_json = json.dumps(answer)
print(answer_json)