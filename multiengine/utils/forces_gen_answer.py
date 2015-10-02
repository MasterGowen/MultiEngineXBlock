import json

student_state = {"id625C76C7":[],"idB028E8B8":[],"idBC3F3678":[],"id4D885A7F":[],"idB43AACD1":[],"id6240A4C5":[],"idE915C649":[],"id000DC0E3":[],"idD3B63CF5":[],"idBC373D4C":["idBC373D4C_117"],"id23E0068F":["id23E0068F_90"],"idDE08433B":["xidDE08433B_269", "xidDE08433B_180"],"idA14EC6E6":[],"idE0991A42":[],"id841E5545":[],"id36AED81D":["id36AED81D_90"],"id371D23FE":["id371D23FE_90"]}

tolerances = {}


def _revert_arrow(variant):
    if variant[0] == 'x':
        return True
    else:
        return False

for key in student_state:
    tolerances[key] = {}
    for variant in student_state[key]:
        tolerance = [[-3, -2, -1, 0, 1, 2, 3]]

        if _revert_arrow(variant):
            tmp_tolerance = []
            for delta in tolerance[0]:
                tmp_tolerance.append(180 + delta)
                variant = variant.replace('x', '')
            tolerance.append(tmp_tolerance)

        tolerances[key][variant] = tolerance

        variant = variant.split('_')
        or_dict = {}
        or_dict["or-and"] = []
        for tolerance_item in tolerance:
            variant_list = []
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