subroutine logical_test(pp, bb)
    USE, INTRINSIC :: ISO_C_Binding
    
    INTEGER, PARAMETER              :: dp =  4
    
    integer(dp), INTENT(IN   ) :: pp
    logical(c_bool), INTENT(OUT) :: bb
    
    if ( pp == 1 ) then
        bb = .FALSE.
    else
        bb = .TRUE.
    end if
end subroutine logical_test   