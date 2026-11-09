"""Ước lượng phân tầng không hoàn lại cho toàn bộ graph A3."""
import math
from fractions import Fraction


def hyper_tail(population, errors, sample_size, observed_errors):
    lower = max(0, sample_size - (population - errors))
    upper = min(observed_errors, sample_size, errors)
    return sum(math.comb(errors, i) * math.comb(population - errors, sample_size - i)
               for i in range(lower, upper + 1))


def stratum(population, labels):
    n = sum(labels.values())
    k = n - labels["DUNG"]
    denom = math.comb(population, n)
    # 2,5% cho mỗi tầng. Loại D khi P_D[số không đúng trong mẫu <= k] <= 1/40.
    lo, hi = k, population + 1
    while hi - lo > 1:
        d = (hi + lo) // 2
        if 40 * hyper_tail(population, d, n, k) <= denom:
            hi = d
        else:
            lo = d
    assert 40 * hyper_tail(population,lo,n,k) > denom
    if lo < population:
        assert 40 * hyper_tail(population,lo+1,n,k) <= denom
    return dict(N=population, n=n, labels=dict(labels), precision=labels["DUNG"]/n,
                exact_upper_errors_97_5=lo, lower_correct_97_5=population-lo,
                lower_precision_97_5=(population-lo)/population)


def combine(inner, outer):
    N = inner["N"] + outer["N"]
    estimated = sum(Fraction(s["N"]*s["labels"]["DUNG"], N*s["n"]) for s in (inner, outer))
    lower = Fraction(inner["lower_correct_97_5"]+outer["lower_correct_97_5"], N)
    return dict(N=N, n=inner["n"]+outer["n"], inner_weight=inner["N"]/N, outer_weight=outer["N"]/N,
                weighted_precision=float(estimated), lower_95=float(lower),
                min_correct_95=lower*N, threshold_exceeded=lower>Fraction(9,10))
