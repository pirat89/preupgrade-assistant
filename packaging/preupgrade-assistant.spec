%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

%global         django_version  1.5.5
%global         south_version   0.8.4
%global         not_fedora ! 0%{?fedora:1}
%global         build_ui %{not_fedora}

Name:           preupgrade-assistant
Version:        2.2.0
Release:        1%{?dist}
Summary:        Preupgrade Assistant advises on feasibility of system upgrade or migration
Group:          System Environment/Libraries
License:        GPLv3+
Source0:        %{name}-%{version}.tar.gz
%if %{not_fedora}
Source1:        Django-%{django_version}.tar.gz
Source2:        south-%{south_version}.tar.gz
Source3:        scripts.txt
%endif # not_fedora

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  rpm-devel
BuildRequires:  python-devel
BuildRequires:  python-setuptools
BuildRequires:  rpm-python
BuildRequires:  diffstat
BuildRequires:  openscap%{?_isa} >= 0:1.2.8-1
BuildRequires:  openscap-engine-sce%{?_isa} >= 0:1.2.8-1
BuildRequires:  openscap-utils%{?_isa} >= 0:1.2.8-1
BuildRequires:  pykickstart
BuildRequires:  python-six
Requires(post):   /sbin/ldconfig
Requires(postun): /sbin/ldconfig
Requires:       coreutils grep gawk
Requires:       sed findutils bash
Requires:       openscap%{?_isa} >= 0:1.2.8-1
Requires:       openscap-engine-sce%{?_isa} >= 0:1.2.8-1
Requires:       openscap-utils%{?_isa} >= 0:1.2.8-1
Requires:       rpm-python
Requires:       redhat-release
Requires:       pykickstart
Requires:       yum-utils
Requires:       python-six
Conflicts:      %{name}-tools < 2.1.0-1
Obsoletes:      %{name} < 2.1.3-1

%description
Preupgrade Assistant analyses the system to assess the feasibility of
upgrading the system to a new major version. Such analysis includes a check for
removed packages, packages replaced by partially incompatible packages, changes
in libraries, users and groups, and various other services. A report of this
analysis can help admins with the system upgrade by identification of potential
troubles and by mitigating some of the incompatibilities. The data gathered
by Preupgrade Assistant can be used for the in-place upgrade or migration of
the system, where the migration means a new system installation that retains as
much of the old system setup as possible.

%if %{build_ui}
%package ui
Summary:    Preupgrade Assistant Web Based User Interface
Group:      System Environment/Libraries
Requires:   %{name}
Requires:   sqlite
Requires:   mod_wsgi
Requires:   %{name} = %{version}-%{release}

%description ui
Graphical interface for Preupgrade Assistant. This can be used
for inspecting results.
%endif # build_ui

%package tools
Summary:    Preupgrade Assistant tools for generating modules
Group:      System Environment/Libraries
Provides:   preupg-xccdf-compose = %{version}-%{release}
Provides:   preupg-create-group-xml = %{version}-%{release}
Requires:   %{name} = %{version}-%{release}
Obsoletes:  %{name}-tools < 2.1.3-1
%description tools
Tools for building/generating modules used by Preupgrade Assistant.
User can specify only INI file and scripts and other stuff needed by
OpenSCAP is generated automatically.

%prep
%setup -n %{name}-%{version} -q

%if %{build_ui}
# Unpack UI-related tarballs
%setup -q -n %{name}-%{version} -D -T -a 1
%setup -q -n %{name}-%{version} -D -T -a 2
%endif # not Fedora

%build
%{__python} setup.py build

%if %{build_ui}
pushd Django-%{django_version}
%{__python} setup.py build
popd
pushd South-%{south_version}
%{__python} setup.py build
popd
%endif # build_ui

%check
# Switch off tests until issue with finding /etc/preupgrade-assistant.conf
# is resolved
#%%{__python} setup.py test

%install
%{__python} setup.py install --skip-build --root=$RPM_BUILD_ROOT

install -d -m 755 $RPM_BUILD_ROOT%{_localstatedir}/log/preupgrade
install -d -m 755 $RPM_BUILD_ROOT%{_mandir}/man1
install -p man/preupg.1 $RPM_BUILD_ROOT%{_mandir}/man1/
install -p man/preupgrade-assistant-api.1 $RPM_BUILD_ROOT%{_mandir}/man1/
install -p man/preupg-content-creator.1 $RPM_BUILD_ROOT%{_mandir}/man1/

%if %{not_fedora}
cp %{SOURCE3} $RPM_BUILD_ROOT%{_datadir}/preupgrade/data/preassessment/
%endif # not_fedora

%if %{build_ui}
######### UI packaging #######################################
mkdir -m 644 -p ${RPM_BUILD_ROOT}%{_sharedstatedir}/preupgrade/{results,upload,static}
touch ${RPM_BUILD_ROOT}%{_sharedstatedir}/preupgrade/{db.sqlite,secret_key}

sed -r \
  -e "s;^DATA_DIR = .*$;DATA_DIR = '%{_sharedstatedir}/preupgrade';" \
  -i ${RPM_BUILD_ROOT}%{python_sitelib}/preupg/ui/settings.py

sed \
    -e 's;WSGI_PATH;%{python_sitelib}/preupg/ui/wsgi.py;g' \
    -e 's;STATIC_PATH;%{_sharedstatedir}/preupgrade/static;g' \
    -i ${RPM_BUILD_ROOT}%{_sysconfdir}/httpd/conf.d/99-preup-httpd.conf.{private,public}

# install django
pushd Django-%{django_version}
%{__python} setup.py install --skip-build --root ${RPM_BUILD_ROOT}
popd
pushd South-%{south_version}
%{__python} setup.py install --skip-build --root ${RPM_BUILD_ROOT}
popd

# remove .po files
find    ${RPM_BUILD_ROOT}%{python_sitelib}/django -name "*.po" | xargs rm -f

# remove bin/django-admin and *.egg-info
rm -rf  ${RPM_BUILD_ROOT}%{_bindir}/django-admin* \
        ${RPM_BUILD_ROOT}%{python_sitelib}/Django-%{django_version}-py*.egg-info \
        ${RPM_BUILD_ROOT}%{python_sitelib}/South-%{south_version}-py*.egg-info

# move django and south to preupg/ui/lib
mkdir   ${RPM_BUILD_ROOT}%{python_sitelib}/preupg/ui/lib
mv      ${RPM_BUILD_ROOT}%{python_sitelib}/{django,south} \
        ${RPM_BUILD_ROOT}%{python_sitelib}/preupg/ui/lib/

######### END UI packaging ################################
%else # do not build UI
# remove UI-related files
rm -rf  ${RPM_BUILD_ROOT}%{python_sitelib}/preupg/ui/
rm -f   ${RPM_BUILD_ROOT}%{_bindir}/preupg-ui-manage
rm -f   ${RPM_BUILD_ROOT}%{_sysconfdir}/httpd/conf.d/99-preup-httpd.conf.*
rm -f   ${RPM_BUILD_ROOT}%{_datadir}/preupgrade/README.ui
%endif # build_ui

######### FILELISTS #######################################
# generate file lists for cleaner files section
get_file_list() {
    find ${RPM_BUILD_ROOT} -type $1 | grep -o $2 \
        | grep -vE "$3" | sed "$4" >> $5
}
### preupgrade-assistant ###
get_file_list f %{python_sitelib}/.*$  "preupg/(ui|creator)|\.pyc$" \
    "s/\.py$/\.py\*/" preupg-filelist
get_file_list d %{python_sitelib}/.*$ "preupg/(ui|creator)|\.pyc$" \
    "s/^/\%dir /" preupg-filelist
%if %{build_ui}
### preupgrade-assistant-ui ###
get_file_list f %{python_sitelib}/preupg/ui.*$ "/ui/settings.py|\.pyc$" \
    "s/\.py$/\.py\*/" preupg-ui-filelist
get_file_list d %{python_sitelib}/preupg/ui.*$ " " \
    "s/^/\%dir /" preupg-ui-filelist
%endif # build_ui
######### END FILELISTS ###################################

%if %{not_fedora}
# clean section should not be used on Fedora per Guidelines
%clean
rm -rf $RPM_BUILD_ROOT
%endif not_fedora

%post
/sbin/ldconfig

######### UI (UN)INSTALLATION scriplets ###################
%if %{build_ui}
%post ui
# populate DB and/or apply DB migrations
su apache - -s /bin/bash -c "preupg-ui-manage syncdb --migrate --noinput" >/dev/null || :
# collect static files
su apache - -s /bin/bash -c "preupg-ui-manage collectstatic --noinput" >/dev/null || :
if [ "$1" == 1 ]; then
    # allow httpd to run preupgrade ui
    setsebool httpd_run_preupgrade on
fi
# restart apache
service httpd condrestart

%postun ui
# $1 holds the number of preupgrade-assistant-ui
# packages which will be left on the system when
# the uninstallation completes.
if [ "$1" == 0 ]; then
    # disallow httpd to run preupgrade ui
    setsebool httpd_run_preupgrade off
    # restart apache
    service httpd condrestart
fi
%endif # build_ui
######### END UI (UN)INSTALLATION scriplets ###############


%postun -p /sbin/ldconfig

%files -f preupg-filelist
%defattr(-,root,root,-)
%attr(0755,root,root) %{_bindir}/preupg
%attr(0755,root,root) %{_bindir}/premigrate
%attr(0755,root,root) %{_bindir}/preupg-kickstart-generator
%dir %{_localstatedir}/log/preupgrade
%dir %{_datadir}/preupgrade/
%dir %{_docdir}/%{name}
%config(noreplace) %{_sysconfdir}/preupgrade-assistant.conf
%{_sysconfdir}/bash_completion.d/preupg.bash
%{_datadir}/preupgrade/data
%{_datadir}/preupgrade/common.sh
%doc %{_datadir}/preupgrade/README
%doc %{_datadir}/preupgrade/README.kickstart
%{!?_licensedir:%global license %%doc}
%license %{_docdir}/%{name}/LICENSE
%attr(0644,root,root) %{_mandir}/man1/preupg.*

%if %{build_ui}
%files ui -f preupg-ui-filelist
%defattr(-,root,root,-)
%attr(0755,root,root) %{_bindir}/preupg-ui-manage
%verify(not md5 size mtime) %config %{python_sitelib}/preupg/ui/settings.py
%{python_sitelib}/preupg/ui/settings.py[c|o]
%config(noreplace) %{_sysconfdir}/httpd/conf.d/99-preup-httpd.conf.*
%attr(0744, apache, apache) %dir %{_sharedstatedir}/preupgrade/
%ghost %config(noreplace) %{_sharedstatedir}/preupgrade/db.sqlite
%ghost %config(noreplace) %{_sharedstatedir}/preupgrade/secret_key
%doc %{_datadir}/preupgrade/README.ui
%endif # build_ui

%files tools
%defattr(-,root,root,-)
%attr(0755,root,root) %{_bindir}/preupg-create-group-xml
%attr(0755,root,root) %{_bindir}/preupg-xccdf-compose
%attr(0755,root,root) %{_bindir}/preupg-content-creator
%{python_sitelib}/preupg/creator/
%attr(0644,root,root) %{_mandir}/man1/preupgrade-assistant-api.*
%attr(0644,root,root) %{_mandir}/man1/preupg-content-creator.*

%changelog
* Wed Nov 16 2016 Michal Bocek <mbocek@redhat.com> - 2.2.0-1
- Initial version of spec file in upstream
