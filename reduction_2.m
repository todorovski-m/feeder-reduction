clc; clear
define_constants;
mpc = runpf('five_branches');
V = mpc.bus(:,VM).*exp(1j*mpc.bus(:, VA)/180*pi);
S = (mpc.bus(:, PD) + 1j*mpc.bus(:, QD))/mpc.baseMVA;
I = conj(S./V);
Z = mpc.branch(:, BR_R) + 1j*mpc.branch(:, BR_X);

n = size(mpc.bus, 1);
J = zeros(n-1,1);
for k=1:n-1
    J(k) = sum(I(k+1:n));
end

fprintf('Exact solution\n');
DV = sum(Z.*J);
DS = sum(Z.*abs(J).^2);
Stot = sum(V.*conj(I)) + DS;
fprintf('DV = %.4f %+.4fj\n', real(DV), imag(DV));
fprintf('DS = %.4f %+.4fj\n', real(DS), imag(DS));
fprintf(' S = %.4f %+.4fj\n', real(Stot), imag(Stot));

fprintf('\nEquivalent - match both DV and DS\n');
Ie2 = conj(sum(Z.*abs(J).^2)/sum(Z.*J));
Ze = sum(Z.*J)/Ie2;
DVe = Ze*Ie2;
DSe = Ze*abs(Ie2)^2;
Ie1 = sum(I) - Ie2;
Stote = V(1)*conj(Ie1) + V(n)*conj(Ie2) + DSe;
fprintf('Ie1 = %.4f %+.4fj\n', real(Ie1), imag(Ie1));
fprintf('Ie2 = %.4f %+.4fj\n', real(Ie2), imag(Ie2));
fprintf('Ze = %.4f %+.4fj\n', real(Ze), imag(Ze));
fprintf('DV = %.4f %+.4fj\n', real(DVe), imag(DVe));
fprintf('DS = %.4f %+.4fj\n', real(DSe), imag(DSe));
fprintf(' S = %.4f %+.4fj\n', real(Stote), imag(Stote));
fprintf('error(DP) = %.2f%%\n', (real(DSe)/real(DS) - 1)*100);

Zs = sum(Z);
g = abs(sum(Z.*J))^2/(Zs * sum(conj(Z).*abs(J).^2));
Ze = g*Zs;
fprintf('Zs = %.4f %+.4fj\n', real(Zs), imag(Zs));
fprintf(' g = %.4f %+.4fj\n', real(g), imag(g));
