"""Word lists used to down-weight ordinary code and to keep language names stable.

Preserved names match the categories Pygments treats as keywords, builtins,
exceptions, and dunder methods. User-defined names are not in this set, so a
rename of project identifiers does not change token fingerprints.
"""

from __future__ import annotations

import keyword

# Builtins and exceptions recognized by Pygments' Python lexer (2.21).
_PY_BUILTINS = """
__import__ abs aiter all any bin bool bytearray breakpoint bytes callable chr
classmethod compile complex delattr dict dir divmod enumerate eval filter float
format frozendict frozenset getattr globals hasattr hash hex id input int
isinstance issubclass iter len list locals map max memoryview min next object
oct open ord pow print property range repr reversed round sentinel set setattr
slice sorted staticmethod str sum super tuple type vars zip
""".split()

_PY_EXCEPTIONS = """
ArithmeticError AssertionError AttributeError BaseException BufferError
BytesWarning DeprecationWarning EOFError EnvironmentError Exception
FloatingPointError FutureWarning GeneratorExit IOError ImportError ImportWarning
IndentationError IndexError KeyError KeyboardInterrupt LookupError MemoryError
NameError NotImplementedError OSError OverflowError PendingDeprecationWarning
ReferenceError ResourceWarning RuntimeError RuntimeWarning StopIteration
SyntaxError SyntaxWarning SystemError SystemExit TabError TypeError
UnboundLocalError UnicodeDecodeError UnicodeEncodeError UnicodeError
UnicodeTranslateError UnicodeWarning UserWarning ValueError VMSError Warning
WindowsError ZeroDivisionError BlockingIOError ChildProcessError ConnectionError
BrokenPipeError ConnectionAbortedError ConnectionRefusedError ConnectionResetError
FileExistsError FileNotFoundError InterruptedError IsADirectoryError
NotADirectoryError PermissionError ProcessLookupError TimeoutError
StopAsyncIteration ModuleNotFoundError RecursionError EncodingWarning
""".split()

_PY_MAGIC = """
__abs__ __add__ __aenter__ __aexit__ __aiter__ __and__ __anext__ __await__
__bool__ __bytes__ __call__ __complex__ __contains__ __del__ __delattr__
__delete__ __delitem__ __dir__ __divmod__ __enter__ __eq__ __exit__ __float__
__floordiv__ __format__ __ge__ __get__ __getattr__ __getattribute__ __getitem__
__gt__ __hash__ __iadd__ __iand__ __ifloordiv__ __ilshift__ __imatmul__ __imod__
__imul__ __index__ __init__ __instancecheck__ __int__ __invert__ __ior__ __ipow__
__irshift__ __isub__ __iter__ __itruediv__ __ixor__ __le__ __len__ __length_hint__
__lshift__ __lt__ __matmul__ __missing__ __mod__ __mul__ __ne__ __neg__ __new__
__next__ __or__ __pos__ __pow__ __prepare__ __radd__ __rand__ __rdivmod__ __repr__
__reversed__ __rfloordiv__ __rlshift__ __rmatmul__ __rmod__ __rmul__ __ror__
__round__ __rpow__ __rrshift__ __rshift__ __rsub__ __rtruediv__ __rxor__ __set__
__setattr__ __setitem__ __str__ __sub__ __subclasscheck__ __truediv__ __xor__
__class__ __dict__ __doc__ __module__ __name__ __qualname__ __slots__ __weakref__
__annotations__ __dataclass_fields__ __orig_bases__ __parameters__
""".split()

PRESERVED_NAMES: frozenset[str] = frozenset(
    set(keyword.kwlist)
    | set(keyword.softkwlist)
    | set(_PY_BUILTINS)
    | set(_PY_EXCEPTIONS)
    | set(_PY_MAGIC)
    | {"True", "False", "None", "self", "cls", "mcs", "Ellipsis", "NotImplemented", "_"}
)

COMMON_IDENTIFIERS: frozenset[str] = frozenset(
    """
    index idx item items value values key keys data result results name names
    path paths file files filename dirname basename directory dir text content
    source src dest dst target input output out tmp temp cache config cfg
    option options opt opts param params argument arguments arg args kwargs
    count total size length offset start end pos position status code type kind
    mode state flag flags user users uid pid gid request response ctx context
    callback handler function func method node nodes child children parent root
    head tail next prev left right mid first last minimum maximum average mean
    string number boolean integer array object map list dict tuple set buffer
    buf line lines row rows col column message messages error errors err exc
    exception info debug warn warning version encoding charset pattern regex
    match group token tokens lexer parser encode decode format split join strip
    replace append remove delete update insert parse load loads dump dumps read
    write open close init main run call apply filter reduce expected actual want
    got assert test tests self cls this super none null nil undefined true false
    filename filepath url uri host port timeout interval retry default payload
    body header headers query params response request client server session
    logger logging utils util helper helpers base abstract generic factory
    manager service handler controller model view schema field fields table
    column columns row record records item element elements entry entries
    valueof tostring prototype length public private protected static void
    return import class struct interface module package namespace using include
    const var let function async await yield break continue case switch elif
    except finally raise throw catch while foreach endif json xml html css
    utf utf8 ascii unicode bytes byte char stream reader writer socket http
    https get post put delete patch options head connect trace localhost
    username password secret token auth error invalid unknown failed failure
    success ok done result retval retcode errno errmsg msg
    """.split()
)

COMMON_WORDS: frozenset[str] = frozenset(
    """
    a about above after again against all also am an and any are as at be because
    been before being below between both but by can could did do does doing down
    during each few for from further had has have having he her here hers herself
    him himself his how i if in into is it its itself just me more most my myself
    no nor not of off on once only or other our ours ourselves out over own same
    she should so some such than that the their theirs them themselves then there
    these they this those through to too under until up very was we were what
    when where which while who whom why will with you your yours yourself
    yourselves able about across after again along already also always among
    another answer around away back because become before begin being below
    better between both bring call came case change children city close come
    consider could course day days did different does doing done down during
    each early end enough even ever every example fact feel few find first
    follow form found from full further general get give given go going good
    great group had hand has have having help her here high him his home how
    however idea important include information interest into issue its just
    keep kind know known large last later lead least leave left less let level
    life like likely line little long look made make man many may mean member
    men might more most move much must name need never new next night not now
    number off often old once one only open order other our out over own part
    people person place plan play point possible present problem program public
    put question quite rather real really right room run said same say second
    see seem set several she should show side since small so some something
    state still such system take than that the their them then there these they
    thing think this those though thought three through time to today together
    too under until up upon us use used using value very want was way we well
    went were what when where whether which while who whole why will with
    within without word work world would write year years you your
    add added adding allow allows amount area ask asked available based become
    before begin behind best bit book both bring build built business called
    cannot certain change changed check child clear close common complete
    consider continue control could create created current data date day
    describe described description detail details determine developed development
    difference different difficult direct does done during early easy either
    else empty end enough entire equal especially even event ever every example
    expect expected experience fact family far feel few field final find fine
    first five follow following form former forward found four free full
    function further game gave general get given gives going gone good got
    government great ground group grow half hand hands hard has have head
    health help her here high history hold home hour hours house however human
    idea important include including increase indeed information instead
    interest into itself keep kept kind knew know known large last later law
    lead learn least leave left less let letter level life light like likely
    line list little live local long look looked looking lost lot love low
    made make makes making man many market may maybe mean means meet member
    men might million mind moment money month months more morning most mother
    move much must name national need needed needs never new news next night
    north not note nothing now number numbers off offer office often old once
    one only onto open opened order other others our out outside over own
    page part particular party past pay people per perhaps person place plan
    play point points political possible power present president pretty private
    probably problem process program provide public pull put question quite
    rather read real really reason receive recent related report research
    result results return right road room run said same saw say says school
    second see seem seemed seems seen sense sent set several she short should
    show showed shown side significant since six small so social some someone
    something sometimes son soon sorry sort sound south space special stand
    start state states still stop story strong student students study such
    sure system table take taken takes taking talk team tell ten term test
    than thank that the their them themselves then there these they thing
    things think third this those though thought three through throughout time
    times to today together told too took top total toward towards town try
    turn two under understand unit until up upon us use used using usually
    value various very view want wanted wants was water way we week weeks well
    went were what whatever when where whether which while white who whole
    whom whose why will with within without woman women word words work worked
    working works world would write written wrong year years yes yet you young
    your
    error invalid missing required unexpected failed failure success warning
    default unknown empty null true false none value input output result
    """.split()
)

COMMON_LITERALS: frozenset[str] = frozenset(
    {
        "",
        " ",
        "\n",
        "\t",
        "utf-8",
        "utf8",
        "ascii",
        "latin-1",
        "utf-16",
        "error",
        "invalid",
        "none",
        "null",
        "true",
        "false",
        "unknown",
        "foo",
        "bar",
        "baz",
        "qux",
        "test",
        "tests",
        "hello",
        "world",
        "hello world",
        "application/json",
        "text/plain",
        "text/html",
        "yes",
        "no",
        "ok",
        "get",
        "post",
        "put",
        "delete",
        "http",
        "https",
        "localhost",
        "expected",
        "actual",
        "todo",
        "fixme",
        "xxx",
        "undefined",
        "object",
        "array",
        "string",
        "number",
        "boolean",
        "{}",
        "[]",
        "()",
        "0",
        "1",
        "-1",
        "a",
        "b",
        "id",
        "name",
        "value",
        "key",
        "data",
        "type",
        "message",
        "success",
        "failure",
    }
)

COMMON_NUMBERS: frozenset[str] = frozenset(
    """
    -1 0 1 2 3 4 5 6 7 8 9 10 16 32 64 100 128 255 256 512 1000 1024 2048 3600
    4096 8192 65535 65536 86400 80 443 8080 8000 3000 5000 5432 3306 27017 22
    200 201 204 301 302 400 401 403 404 500 201 204
    3.14 3.1416 3.14159 3.14159265 2.71828 2.718 1.0 0.0 0.5 2.0 10.0 100.0
    """.split()
)

# Whole words that are established misspellings. Shared ones are high-weight
# artifacts because ordinary projects do not land on the same typo by chance.
MISSPELLINGS: frozenset[str] = frozenset(
    """
    occured occurence seperated seperator seperate recieve recieved reciept
    definately definate existance existant threshhold succesful sucessful
    occassion occassionally guage accomodate accomodation untill wich teh waht
    lenght lenghts widht heigth hieght adress addres begining calender colleage
    commited commitee comparision concensus concious dependancy dependant
    dessicate dilema dissapear dissapoint enviroment exersize explaination
    facinate finaly foriegn fourty freind futher gaurd grammer harrass
    independant knowlege libary liason lisence looses maintainance millenium
    miniscule mispell neccessary noticable occurance occuring orignal persistant
    playright posession prefered priviledge publically quater reccomend refered
    relevent religous repitition restaraunt seige sentance similiar speach
    supercede suprise tommorow tounge truely unecessary unforseen unfortunatly
    usefull vaccuum vegitable writting yeild
    """.split()
)
