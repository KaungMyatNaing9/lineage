from n0 .n1 import n2 


def n3 ():
    n4 ={"angstrom-flange"}
    assert n2 ("Ångström flange",n4 =n4 )=="angstrom-flange-2"
    assert n2 ("Þ-flange torque 48271")=="th-flange-torque-48271"


def n5 ():
    try :
        n2 ("flange",n6 ="--")
    except ValueError as n7 :
        assert "seperator"in str (n7 )
    else :
        raise AssertionError ("expected a separator failure")
