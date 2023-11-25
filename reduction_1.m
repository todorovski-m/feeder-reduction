clc; clear
define_constants;
mpc = runpf('two_branches');
V = mpc.bus(:,VM).*exp(1j*mpc.bus(:, VA)/180*pi);
S = (mpc.bus(:, PD) + 1j*mpc.bus(:, QD))/mpc.baseMVA;
I = conj(S./V);
J(1) = I(2) + I(3);
J(2) = I(3);
Z = mpc.branch(:, BR_R) + 1j*mpc.branch(:, BR_X);

fprintf('Exact solution\n');
DV = Z(1)*J(1) + Z(2)*J(2);
DS = Z(1)*abs(J(1))^2 + Z(2)*abs(J(2))^2;
Stot = sum(V.*conj(I)) + DS;
fprintf('DV = %.4f %+.4fj\n', real(DV), imag(DV));
fprintf('DS = %.4f %+.4fj\n', real(DS), imag(DS));
fprintf(' S = %.4f %+.4fj\n', real(Stot), imag(Stot));

fprintf('\nEquivalent - match DV only\n');
Ze = Z(1) + Z(2);
Ie1 = I(1) + Z(2)/(Z(1) + Z(2))*I(2);
Ie2 = I(3) + Z(1)/(Z(1) + Z(2))*I(2);
DVe = Ze*Ie2;
DSe = Ze*abs(Ie2)^2;
Stote = V(1)*conj(Ie1) + V(3)*conj(Ie2) + DSe;
fprintf('Ie1 = %.4f %+.4fj\n', real(Ie1), imag(Ie1));
fprintf('Ie2 = %.4f %+.4fj\n', real(Ie2), imag(Ie2));
fprintf('DV = %.4f %+.4fj\n', real(DVe), imag(DVe));
fprintf('DS = %.4f %+.4fj\n', real(DSe), imag(DSe));
fprintf(' S = %.4f %+.4fj\n', real(Stote), imag(Stote));
fprintf('error(DP) = %.2f%%\n', (real(DSe)/real(DS) - 1)*100);

fprintf('\nEquivalent - match both DV and DS\n');
Ie2 = I(3) + I(2)*conj(1 + Z(2)*I(3)/(Z(1)*(I(2) + I(3))))^-1;
Ze = (Z(1)*(I(2) + I(3)) + Z(2)*I(3))/Ie2;
DVe = Ze*Ie2;
DSe = Ze*abs(Ie2)^2;
Ie1 = sum(I) - Ie2;
Stote = V(1)*conj(Ie1) + V(3)*conj(Ie2) + DSe;
fprintf('Ie1 = %.4f %+.4fj\n', real(Ie1), imag(Ie1));
fprintf('Ie2 = %.4f %+.4fj\n', real(Ie2), imag(Ie2));
fprintf('Ze = %.4f %+.4fj\n', real(Ze), imag(Ze));
fprintf('DV = %.4f %+.4fj\n', real(DVe), imag(DVe));
fprintf('DS = %.4f %+.4fj\n', real(DSe), imag(DSe));
fprintf(' S = %.4f %+.4fj\n', real(Stote), imag(Stote));
fprintf('error(DP) = %.2f%%\n', (real(DSe)/real(DS) - 1)*100);
