"""Independent reference: exact six-cell algebra and half-integer gamma sums.

No HASHLAB imports. Production uses a general gamma series/continued fraction;
this reference uses finite integer/half-integer upward recurrence, with an
independently evaluated erfc base. Decimal precision is 200 digits.
"""
from decimal import Decimal, localcontext
from fractions import Fraction

PI = Decimal('3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196')


def chi_reference(q, df):
    with localcontext() as ctx:
        ctx.prec = 200
        ctx.Emin = -999999999999
        ctx.Emax = 999999999999
        x = Decimal(q.numerator)/Decimal(q.denominator)/2
        if not x:
            return Decimal(1), Decimal(0)
        a = Decimal(df)/2
        # Certified lower-tail Chernoff bound. Values closer to one than
        # exp(-250) are pinned as one/log-zero with that explicit error bound;
        # avoid cancellation when the true complement needs thousands of digits.
        if x < a and a-x+a*(x/a).ln() < -250:
            return Decimal(1), Decimal(0)
        if df % 2 == 0:
            term = total = Decimal(1)
            for k in range(1, df//2):
                term *= x/k
                total += term
            tail = (-x).exp()*total
        else:
            root_pi = PI.sqrt()
            if x <= 100:
                # Lower gamma(.5) positive power series; subtract at 200 digits.
                term = total = Decimal(2)
                k = 0
                while True:
                    k += 1
                    term *= x/(Decimal(k)+Decimal('.5'))
                    total += term
                    if abs(term) < abs(total)*Decimal('1e-190'): break
                base = 1-(-x).exp()*x.sqrt()/root_pi*total
            else:
                # Alternating erfc asymptotic series, bounded by first omitted
                # term while terms decrease. Stop before the least term.
                term = total = Decimal(1)
                k = 0
                while True:
                    k += 1
                    next_term = -term*(2*k-1)/(2*x)
                    if abs(next_term) >= abs(term): break
                    total += next_term
                    term = next_term
                    if abs(term) < abs(total)*Decimal('1e-150'): break
                base = (-x).exp()/root_pi/x.sqrt()*total
            tail = base
            # Q(a+1,x)=Q(a,x)+x**a*exp(-x)/Gamma(a+1), a=.5 initially.
            term = 2*x.sqrt()*(-x).exp()/root_pi
            a = Decimal('.5')
            for _ in range((df-1)//2):
                tail += term
                a += 1
                term *= x/a
        if not 0 < tail <= 1:
            raise ArithmeticError('reference precision insufficient')
        return +tail, +tail.ln()


def pearson(observed, expected):
    return sum(((Fraction(o)-e)**2/e for o,e in zip(observed,expected)),Fraction())


def cluster_q(counts):
    p = Fraction(sum(counts),15000000)
    # Explicit success/failure cells, rather than production dispersion formula.
    observed = list(counts)+[10000-k for k in counts]
    expected = [10000*p]*1500+[10000*(1-p)]*1500
    return pearson(observed,expected)


def grouped_q(trials, successes):
    t = [sum(trials[:4]),trials[4],trials[5]]
    k = [sum(successes[:4]),successes[4],successes[5]]
    p = Fraction(sum(k),sum(t))
    return pearson(k+[n-s for n,s in zip(t,k)],
                   [n*p for n in t]+[n*(1-p) for n in t])
