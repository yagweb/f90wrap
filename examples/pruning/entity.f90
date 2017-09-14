module entity

    type point
        integer :: x
        integer :: y
    end type point

    type segment
        integer :: num
        type(point) :: x(2)
    end type segment

contains

    subroutine hello(res)
        integer, intent(out) :: res
        res = 123
    end subroutine hello

    subroutine hello2(x, res)
        integer, intent(in) :: x
        integer, intent(out) :: res
        res = x * 100
    end subroutine hello2

end module entity