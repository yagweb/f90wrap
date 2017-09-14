module test

    use entity, only : pt => point

contains 

    subroutine add(pp)
        !use entity, only : pt => point
        type(pt), intent(inout) :: pp
        pp%x = pp%x + 1
        pp%y = pp%y + 1
    end subroutine add

    subroutine add1(x)
        use entity, only : point
        type(point), intent(inout) :: x
        x%x = x%x + 1
        x%y = x%y + 1
    end subroutine add1

    subroutine reverse(x)
        use entity, only : point, segment
        type(segment), intent(inout) :: x
        type(point) :: temp
        temp = x%x(1)
        x%x(1) = x%x(2)
        x%x(2) = temp
    end subroutine reverse

end module test